package mlflow

import (
	"context"
	"strings"

	"github.com/kubeflow/pipelines/backend/src/apiserver/client"
	"github.com/kubeflow/pipelines/backend/src/apiserver/common"
	"github.com/kubeflow/pipelines/backend/src/common/util"
	"github.com/pkg/errors"
	"google.golang.org/grpc/metadata"
	authorizationv1 "k8s.io/api/authorization/v1"
	v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

const (
	AuthorizationEnabledConfigKey = "plugins.mlflow.authorizationEnabled"
	ExperimentGroup               = "mlflow.kubeflow.org"
	ExperimentResource            = "experiments"
)

func AuthorizeExperimentAction(
	ctx context.Context,
	namespace string,
	sarClient client.SubjectAccessReviewInterface,
	isAuthorized func(context.Context, *authorizationv1.ResourceAttributes) error,
) error {
	resourceAttributes := &authorizationv1.ResourceAttributes{
		Namespace: namespace,
		Group:     ExperimentGroup,
		Resource:  ExperimentResource,
		Verb:      common.RbacResourceVerbCreate,
	}
	if common.IsMultiUserMode() {
		return isAuthorized(ctx, resourceAttributes)
	}
	if !common.GetBoolConfigWithDefault(AuthorizationEnabledConfigKey, false) {
		return nil
	}
	userIdentity, err := getForwardedUserIdentity(ctx)
	if err != nil {
		return err
	}
	if sarClient == nil {
		return util.NewInternalServerError(errors.New("subject access review client is nil"), "Failed to create SubjectAccessReview for user '%s' and MLflow experiment access", userIdentity)
	}
	result, err := sarClient.Create(
		ctx,
		&authorizationv1.SubjectAccessReview{
			Spec: authorizationv1.SubjectAccessReviewSpec{
				User: userIdentity,
				ResourceAttributes: &authorizationv1.ResourceAttributes{
					Namespace: namespace,
					Group:     ExperimentGroup,
					Resource:  ExperimentResource,
					Verb:      common.RbacResourceVerbCreate,
				},
			},
		},
		v1.CreateOptions{},
	)
	if err != nil {
		return util.NewInternalServerError(err, "Failed to create SubjectAccessReview for user '%s' and MLflow experiment access", userIdentity)
	}
	if !result.Status.Allowed {
		return util.NewPermissionDeniedError(
			errors.New("Unauthorized access"),
			"User '%s' is not authorized to access MLflow experiments with reason: %s",
			userIdentity,
			result.Status.Reason,
		)
	}
	return nil
}

func getForwardedUserIdentity(ctx context.Context) (string, error) {
	if ctx == nil {
		return "", util.NewUnauthenticatedError(errors.New("Context is nil"), "Failed to check authorization. User identity is empty in the request header")
	}
	md, ok := metadata.FromIncomingContext(ctx)
	if !ok {
		return "", util.NewUnauthenticatedError(errors.New("metadata is missing"), "Failed to check authorization. User identity is empty in the request header")
	}
	headerName := strings.ToLower(common.GetKubeflowUserIDHeader())
	values := md.Get(headerName)
	if len(values) == 0 {
		values = md.Get(common.GetKubeflowUserIDHeader())
	}
	if len(values) == 0 {
		return "", util.NewUnauthenticatedError(errors.New("user identity header is missing"), "Failed to check authorization. User identity is empty in the request header")
	}
	userIdentity := values[0]
	if prefix := common.GetKubeflowUserIDPrefix(); prefix != "" && strings.HasPrefix(userIdentity, prefix) {
		userIdentity = strings.TrimPrefix(userIdentity, prefix)
	}
	if userIdentity == "" {
		return "", util.NewUnauthenticatedError(errors.New("user identity is empty"), "Failed to check authorization. User identity is empty in the request header")
	}
	return userIdentity, nil
}
