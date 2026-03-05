package mlflow

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestClientGetExperimentByNameAndCreateRun(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "Bearer test-token", r.Header.Get("Authorization"))
		assert.Equal(t, "ns1", r.Header.Get("X-MLflow-Workspace"))
		switch r.URL.Path {
		case "/api/2.0/mlflow/experiments/get-by-name":
			assert.Equal(t, "my-exp", r.URL.Query().Get("experiment_name"))
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte(`{"experiment":{"experiment_id":"42","name":"my-exp"}}`))
		case "/api/2.0/mlflow/runs/create":
			body, _ := io.ReadAll(r.Body)
			assert.Contains(t, string(body), `"experiment_id":"42"`)
			assert.Contains(t, string(body), `"run_name":"kfp-run"`)
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte(`{"run":{"info":{"run_id":"run-1"}}}`))
		default:
			t.Fatalf("unexpected path %s", r.URL.Path)
		}
	}))
	defer server.Close()

	client, err := NewClient(Config{
		Endpoint:          server.URL,
		HTTPClient:        &http.Client{Timeout: 5 * time.Second},
		AuthType:          AuthTypeBearer,
		BearerToken:       "test-token",
		WorkspacesEnabled: true,
		Workspace:         "ns1",
	})
	require.NoError(t, err)

	experiment, err := client.GetExperimentByName(context.Background(), "my-exp")
	require.NoError(t, err)
	assert.Equal(t, "42", experiment.ID)

	runID, err := client.CreateRun(context.Background(), experiment.ID, "kfp-run", nil)
	require.NoError(t, err)
	assert.Equal(t, "run-1", runID)
}

func TestClientSetTagAndLogBatch(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/api/2.0/mlflow/runs/set-tag":
			var req map[string]string
			require.NoError(t, json.NewDecoder(r.Body).Decode(&req))
			assert.Equal(t, "run-1", req["run_id"])
			assert.Equal(t, "kfp.pipeline_run_id", req["key"])
		case "/api/2.0/mlflow/runs/log-batch":
			var req map[string]interface{}
			require.NoError(t, json.NewDecoder(r.Body).Decode(&req))
			assert.Equal(t, "run-1", req["run_id"])
		default:
			t.Fatalf("unexpected path %s", r.URL.Path)
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{}`))
	}))
	defer server.Close()

	client, err := NewClient(Config{Endpoint: server.URL})
	require.NoError(t, err)
	require.NoError(t, client.SetTag(context.Background(), "run-1", "kfp.pipeline_run_id", "kfp-run-1"))
	require.NoError(t, client.LogBatch(context.Background(), "run-1", nil, nil, nil))
}

func TestErrorHelpers(t *testing.T) {
	assert.True(t, IsNotFoundError(&HTTPError{StatusCode: http.StatusNotFound}))
	assert.True(t, IsAlreadyExistsError(&HTTPError{ErrorCode: "RESOURCE_ALREADY_EXISTS"}))
	assert.False(t, IsAlreadyExistsError(assert.AnError))
}
