// Code generated by go-swagger; DO NOT EDIT.

package pipeline_service

// This file was generated by the swagger tool.
// Editing this file might prove futile when you re-run the swagger generate command

import (
	"context"
	"net/http"
	"time"

	"github.com/go-openapi/errors"
	"github.com/go-openapi/runtime"
	cr "github.com/go-openapi/runtime/client"

	strfmt "github.com/go-openapi/strfmt"
)

// NewPipelineServiceDeletePipelineVersionV1Params creates a new PipelineServiceDeletePipelineVersionV1Params object
// with the default values initialized.
func NewPipelineServiceDeletePipelineVersionV1Params() *PipelineServiceDeletePipelineVersionV1Params {
	var ()
	return &PipelineServiceDeletePipelineVersionV1Params{

		timeout: cr.DefaultTimeout,
	}
}

// NewPipelineServiceDeletePipelineVersionV1ParamsWithTimeout creates a new PipelineServiceDeletePipelineVersionV1Params object
// with the default values initialized, and the ability to set a timeout on a request
func NewPipelineServiceDeletePipelineVersionV1ParamsWithTimeout(timeout time.Duration) *PipelineServiceDeletePipelineVersionV1Params {
	var ()
	return &PipelineServiceDeletePipelineVersionV1Params{

		timeout: timeout,
	}
}

// NewPipelineServiceDeletePipelineVersionV1ParamsWithContext creates a new PipelineServiceDeletePipelineVersionV1Params object
// with the default values initialized, and the ability to set a context for a request
func NewPipelineServiceDeletePipelineVersionV1ParamsWithContext(ctx context.Context) *PipelineServiceDeletePipelineVersionV1Params {
	var ()
	return &PipelineServiceDeletePipelineVersionV1Params{

		Context: ctx,
	}
}

// NewPipelineServiceDeletePipelineVersionV1ParamsWithHTTPClient creates a new PipelineServiceDeletePipelineVersionV1Params object
// with the default values initialized, and the ability to set a custom HTTPClient for a request
func NewPipelineServiceDeletePipelineVersionV1ParamsWithHTTPClient(client *http.Client) *PipelineServiceDeletePipelineVersionV1Params {
	var ()
	return &PipelineServiceDeletePipelineVersionV1Params{
		HTTPClient: client,
	}
}

/*PipelineServiceDeletePipelineVersionV1Params contains all the parameters to send to the API endpoint
for the pipeline service delete pipeline version v1 operation typically these are written to a http.Request
*/
type PipelineServiceDeletePipelineVersionV1Params struct {

	/*VersionID
	  The ID of the pipeline version to be deleted.

	*/
	VersionID string

	timeout    time.Duration
	Context    context.Context
	HTTPClient *http.Client
}

// WithTimeout adds the timeout to the pipeline service delete pipeline version v1 params
func (o *PipelineServiceDeletePipelineVersionV1Params) WithTimeout(timeout time.Duration) *PipelineServiceDeletePipelineVersionV1Params {
	o.SetTimeout(timeout)
	return o
}

// SetTimeout adds the timeout to the pipeline service delete pipeline version v1 params
func (o *PipelineServiceDeletePipelineVersionV1Params) SetTimeout(timeout time.Duration) {
	o.timeout = timeout
}

// WithContext adds the context to the pipeline service delete pipeline version v1 params
func (o *PipelineServiceDeletePipelineVersionV1Params) WithContext(ctx context.Context) *PipelineServiceDeletePipelineVersionV1Params {
	o.SetContext(ctx)
	return o
}

// SetContext adds the context to the pipeline service delete pipeline version v1 params
func (o *PipelineServiceDeletePipelineVersionV1Params) SetContext(ctx context.Context) {
	o.Context = ctx
}

// WithHTTPClient adds the HTTPClient to the pipeline service delete pipeline version v1 params
func (o *PipelineServiceDeletePipelineVersionV1Params) WithHTTPClient(client *http.Client) *PipelineServiceDeletePipelineVersionV1Params {
	o.SetHTTPClient(client)
	return o
}

// SetHTTPClient adds the HTTPClient to the pipeline service delete pipeline version v1 params
func (o *PipelineServiceDeletePipelineVersionV1Params) SetHTTPClient(client *http.Client) {
	o.HTTPClient = client
}

// WithVersionID adds the versionID to the pipeline service delete pipeline version v1 params
func (o *PipelineServiceDeletePipelineVersionV1Params) WithVersionID(versionID string) *PipelineServiceDeletePipelineVersionV1Params {
	o.SetVersionID(versionID)
	return o
}

// SetVersionID adds the versionId to the pipeline service delete pipeline version v1 params
func (o *PipelineServiceDeletePipelineVersionV1Params) SetVersionID(versionID string) {
	o.VersionID = versionID
}

// WriteToRequest writes these params to a swagger request
func (o *PipelineServiceDeletePipelineVersionV1Params) WriteToRequest(r runtime.ClientRequest, reg strfmt.Registry) error {

	if err := r.SetTimeout(o.timeout); err != nil {
		return err
	}
	var res []error

	// path param version_id
	if err := r.SetPathParam("version_id", o.VersionID); err != nil {
		return err
	}

	if len(res) > 0 {
		return errors.CompositeValidationError(res...)
	}
	return nil
}
