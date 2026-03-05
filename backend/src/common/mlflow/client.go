package mlflow

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/cenkalti/backoff"
)

const (
	DefaultAuthType      = "kubernetes"
	AuthTypeBearer       = "bearer"
	AuthTypeBasicAuth    = "basic-auth"
	DefaultRetryInitial  = 500 * time.Millisecond
	DefaultRetryMax      = 5 * time.Second
	DefaultRetryElapsed  = 30 * time.Second
	workspaceHeaderKey   = "X-MLflow-Workspace"
	contentTypeHeaderKey = "Content-Type"
	contentTypeJSON      = "application/json"
)

type Config struct {
	Endpoint          string
	HTTPClient        *http.Client
	AuthType          string
	BearerToken       string
	BasicAuthUsername string
	BasicAuthPassword string
	WorkspacesEnabled bool
	Workspace         string
	Retry             RetryPolicy
}

type RetryPolicy struct {
	InitialInterval time.Duration
	MaxInterval     time.Duration
	MaxElapsedTime  time.Duration
	Multiplier      float64
}

type Client struct {
	baseURL *url.URL
	http    *http.Client
	cfg     Config
}

type ErrorResponse struct {
	ErrorCode string `json:"error_code"`
	Message   string `json:"message"`
}

type HTTPError struct {
	StatusCode int
	ErrorCode  string
	Message    string
}

func (e *HTTPError) Error() string {
	if e == nil {
		return ""
	}
	if e.ErrorCode != "" {
		return fmt.Sprintf("mlflow request failed: status=%d error_code=%s message=%s", e.StatusCode, e.ErrorCode, e.Message)
	}
	if e.Message != "" {
		return fmt.Sprintf("mlflow request failed: status=%d message=%s", e.StatusCode, e.Message)
	}
	return fmt.Sprintf("mlflow request failed: status=%d", e.StatusCode)
}

type Experiment struct {
	ID   string
	Name string
}

type Tag struct {
	Key   string `json:"key"`
	Value string `json:"value"`
}

type Param struct {
	Key   string `json:"key"`
	Value string `json:"value"`
}

type Metric struct {
	Key       string  `json:"key"`
	Value     float64 `json:"value"`
	Timestamp int64   `json:"timestamp"`
	Step      int64   `json:"step"`
}

type SearchRunsResponse struct {
	Runs          []json.RawMessage `json:"runs"`
	NextPageToken string            `json:"next_page_token"`
}

func NewClient(cfg Config) (*Client, error) {
	if cfg.Endpoint == "" {
		return nil, fmt.Errorf("mlflow endpoint is required")
	}
	baseURL, err := url.Parse(cfg.Endpoint)
	if err != nil || baseURL.Scheme == "" || baseURL.Host == "" {
		return nil, fmt.Errorf("invalid mlflow endpoint %q", cfg.Endpoint)
	}
	if cfg.HTTPClient == nil {
		cfg.HTTPClient = &http.Client{Timeout: 30 * time.Second}
	}
	if cfg.AuthType == "" {
		cfg.AuthType = DefaultAuthType
	}
	if cfg.Retry.InitialInterval <= 0 {
		cfg.Retry.InitialInterval = DefaultRetryInitial
	}
	if cfg.Retry.MaxInterval <= 0 {
		cfg.Retry.MaxInterval = DefaultRetryMax
	}
	if cfg.Retry.MaxElapsedTime <= 0 {
		cfg.Retry.MaxElapsedTime = DefaultRetryElapsed
	}
	if cfg.Retry.Multiplier <= 0 {
		cfg.Retry.Multiplier = 2.0
	}
	return &Client{
		baseURL: baseURL,
		http:    cfg.HTTPClient,
		cfg:     cfg,
	}, nil
}

func (c *Client) CreateExperiment(ctx context.Context, name string, description *string) (string, error) {
	payload := map[string]interface{}{"name": name}
	if description != nil {
		payload["description"] = *description
	}
	var resp struct {
		ExperimentID string `json:"experiment_id"`
	}
	if err := c.doJSON(ctx, http.MethodPost, "/api/2.0/mlflow/experiments/create", payload, &resp); err != nil {
		return "", err
	}
	if resp.ExperimentID == "" {
		return "", fmt.Errorf("mlflow create experiment response missing experiment_id")
	}
	return resp.ExperimentID, nil
}

func (c *Client) GetExperimentByName(ctx context.Context, name string) (*Experiment, error) {
	path := "/api/2.0/mlflow/experiments/get-by-name?experiment_name=" + url.QueryEscape(name)
	var resp struct {
		Experiment struct {
			ExperimentID string `json:"experiment_id"`
			Name         string `json:"name"`
		} `json:"experiment"`
	}
	if err := c.doJSON(ctx, http.MethodGet, path, nil, &resp); err != nil {
		return nil, err
	}
	if resp.Experiment.ExperimentID == "" {
		return nil, fmt.Errorf("mlflow get-by-name response missing experiment_id")
	}
	result := &Experiment{ID: resp.Experiment.ExperimentID, Name: resp.Experiment.Name}
	if result.Name == "" {
		result.Name = name
	}
	return result, nil
}

func (c *Client) CreateRun(ctx context.Context, experimentID string, runName string, tags []Tag) (string, error) {
	payload := map[string]interface{}{
		"experiment_id": experimentID,
	}
	if runName != "" {
		payload["run_name"] = runName
	}
	if len(tags) > 0 {
		payload["tags"] = tags
	}
	var resp struct {
		Run struct {
			Info struct {
				RunID   string `json:"run_id"`
				RunUUID string `json:"run_uuid"`
			} `json:"info"`
		} `json:"run"`
	}
	if err := c.doJSON(ctx, http.MethodPost, "/api/2.0/mlflow/runs/create", payload, &resp); err != nil {
		return "", err
	}
	runID := resp.Run.Info.RunID
	if runID == "" {
		runID = resp.Run.Info.RunUUID
	}
	if runID == "" {
		return "", fmt.Errorf("mlflow create run response missing run_id")
	}
	return runID, nil
}

func (c *Client) SetTag(ctx context.Context, runID, key, value string) error {
	payload := map[string]string{
		"run_id": runID,
		"key":    key,
		"value":  value,
	}
	return c.doJSON(ctx, http.MethodPost, "/api/2.0/mlflow/runs/set-tag", payload, nil)
}

func (c *Client) UpdateRun(ctx context.Context, runID, status string, endTimeMs *int64) error {
	payload := map[string]interface{}{
		"run_id": runID,
		"status": status,
	}
	if endTimeMs != nil {
		payload["end_time"] = *endTimeMs
	}
	return c.doJSON(ctx, http.MethodPost, "/api/2.0/mlflow/runs/update", payload, nil)
}

func (c *Client) SearchRuns(ctx context.Context, experimentIDs []string, filter string, maxResults int, pageToken string) (*SearchRunsResponse, error) {
	payload := map[string]interface{}{
		"experiment_ids": experimentIDs,
	}
	if filter != "" {
		payload["filter"] = filter
	}
	if maxResults > 0 {
		payload["max_results"] = maxResults
	}
	if pageToken != "" {
		payload["page_token"] = pageToken
	}
	var resp SearchRunsResponse
	if err := c.doJSON(ctx, http.MethodPost, "/api/2.0/mlflow/runs/search", payload, &resp); err != nil {
		return nil, err
	}
	return &resp, nil
}

func (c *Client) LogBatch(ctx context.Context, runID string, metrics []Metric, params []Param, tags []Tag) error {
	payload := map[string]interface{}{
		"run_id": runID,
	}
	if len(metrics) > 0 {
		payload["metrics"] = metrics
	}
	if len(params) > 0 {
		payload["params"] = params
	}
	if len(tags) > 0 {
		payload["tags"] = tags
	}
	return c.doJSON(ctx, http.MethodPost, "/api/2.0/mlflow/runs/log-batch", payload, nil)
}

func IsNotFoundError(err error) bool {
	httpErr, ok := err.(*HTTPError)
	if !ok {
		return false
	}
	return httpErr.StatusCode == http.StatusNotFound || httpErr.ErrorCode == "RESOURCE_DOES_NOT_EXIST"
}

func IsAlreadyExistsError(err error) bool {
	httpErr, ok := err.(*HTTPError)
	if !ok {
		return false
	}
	return httpErr.StatusCode == http.StatusConflict || httpErr.ErrorCode == "RESOURCE_ALREADY_EXISTS"
}

func (c *Client) doJSON(ctx context.Context, method string, path string, requestBody interface{}, responseBody interface{}) error {
	var requestBytes []byte
	var err error
	if requestBody != nil {
		requestBytes, err = json.Marshal(requestBody)
		if err != nil {
			return fmt.Errorf("marshal request body: %w", err)
		}
	}
	op := func() error {
		requestURL := *c.baseURL
		requestURL.Path = strings.TrimRight(requestURL.Path, "/") + path
		var body io.Reader
		if requestBytes != nil {
			body = bytes.NewReader(requestBytes)
		}
		req, err := http.NewRequestWithContext(ctx, method, requestURL.String(), body)
		if err != nil {
			return backoff.Permanent(err)
		}
		if requestBytes != nil {
			req.Header.Set(contentTypeHeaderKey, contentTypeJSON)
		}
		c.applyHeaders(req)
		resp, err := c.http.Do(req)
		if err != nil {
			return err
		}
		defer resp.Body.Close()
		data, err := io.ReadAll(resp.Body)
		if err != nil {
			return err
		}
		if resp.StatusCode < 200 || resp.StatusCode >= 300 {
			httpErr := parseHTTPError(resp.StatusCode, data)
			if resp.StatusCode >= 500 || resp.StatusCode == http.StatusTooManyRequests {
				return httpErr
			}
			return backoff.Permanent(httpErr)
		}
		if responseBody == nil || len(data) == 0 {
			return nil
		}
		if err := json.Unmarshal(data, responseBody); err != nil {
			return backoff.Permanent(fmt.Errorf("unmarshal response body: %w", err))
		}
		return nil
	}
	return backoff.Retry(op, c.newBackOff())
}

func (c *Client) applyHeaders(req *http.Request) {
	switch strings.ToLower(c.cfg.AuthType) {
	case DefaultAuthType, AuthTypeBearer:
		if c.cfg.BearerToken != "" {
			req.Header.Set("Authorization", "Bearer "+c.cfg.BearerToken)
		}
	case AuthTypeBasicAuth:
		req.SetBasicAuth(c.cfg.BasicAuthUsername, c.cfg.BasicAuthPassword)
	}
	if c.cfg.WorkspacesEnabled && c.cfg.Workspace != "" {
		req.Header.Set(workspaceHeaderKey, c.cfg.Workspace)
	}
}

func (c *Client) newBackOff() *backoff.ExponentialBackOff {
	b := backoff.NewExponentialBackOff()
	b.InitialInterval = c.cfg.Retry.InitialInterval
	b.MaxInterval = c.cfg.Retry.MaxInterval
	b.MaxElapsedTime = c.cfg.Retry.MaxElapsedTime
	b.Multiplier = c.cfg.Retry.Multiplier
	b.Reset()
	return b
}

func parseHTTPError(statusCode int, payload []byte) error {
	errResp := &ErrorResponse{}
	if len(payload) > 0 && json.Unmarshal(payload, errResp) == nil && (errResp.ErrorCode != "" || errResp.Message != "") {
		return &HTTPError{
			StatusCode: statusCode,
			ErrorCode:  errResp.ErrorCode,
			Message:    errResp.Message,
		}
	}
	message := strings.TrimSpace(string(payload))
	if message == "" {
		message = http.StatusText(statusCode)
	}
	return &HTTPError{
		StatusCode: statusCode,
		Message:    message,
	}
}
