// Code generated by go-swagger; DO NOT EDIT.

package pipeline_service

// This file was generated by the swagger tool.
// Editing this file might prove futile when you re-run the swagger generate command

import (
	"fmt"
	"io"

	"github.com/go-openapi/runtime"

	strfmt "github.com/go-openapi/strfmt"

	pipeline_model "github.com/kubeflow/pipelines/backend/api/v1beta1/go_http_client/pipeline_model"
)

// PipelineServiceGetTemplateReader is a Reader for the PipelineServiceGetTemplate structure.
type PipelineServiceGetTemplateReader struct {
	formats strfmt.Registry
}

// ReadResponse reads a server response into the received o.
func (o *PipelineServiceGetTemplateReader) ReadResponse(response runtime.ClientResponse, consumer runtime.Consumer) (interface{}, error) {
	switch response.Code() {

	case 200:
		result := NewPipelineServiceGetTemplateOK()
		if err := result.readResponse(response, consumer, o.formats); err != nil {
			return nil, err
		}
		return result, nil

	default:
		result := NewPipelineServiceGetTemplateDefault(response.Code())
		if err := result.readResponse(response, consumer, o.formats); err != nil {
			return nil, err
		}
		if response.Code()/100 == 2 {
			return result, nil
		}
		return nil, result
	}
}

// NewPipelineServiceGetTemplateOK creates a PipelineServiceGetTemplateOK with default headers values
func NewPipelineServiceGetTemplateOK() *PipelineServiceGetTemplateOK {
	return &PipelineServiceGetTemplateOK{}
}

/*PipelineServiceGetTemplateOK handles this case with default header values.

A successful response.
*/
type PipelineServiceGetTemplateOK struct {
	Payload *pipeline_model.APIGetTemplateResponse
}

func (o *PipelineServiceGetTemplateOK) Error() string {
	return fmt.Sprintf("[GET /apis/v1beta1/pipelines/{id}/templates][%d] pipelineServiceGetTemplateOK  %+v", 200, o.Payload)
}

func (o *PipelineServiceGetTemplateOK) readResponse(response runtime.ClientResponse, consumer runtime.Consumer, formats strfmt.Registry) error {

	o.Payload = new(pipeline_model.APIGetTemplateResponse)

	// response payload
	if err := consumer.Consume(response.Body(), o.Payload); err != nil && err != io.EOF {
		return err
	}

	return nil
}

// NewPipelineServiceGetTemplateDefault creates a PipelineServiceGetTemplateDefault with default headers values
func NewPipelineServiceGetTemplateDefault(code int) *PipelineServiceGetTemplateDefault {
	return &PipelineServiceGetTemplateDefault{
		_statusCode: code,
	}
}

/*PipelineServiceGetTemplateDefault handles this case with default header values.

An unexpected error response.
*/
type PipelineServiceGetTemplateDefault struct {
	_statusCode int

	Payload *pipeline_model.GatewayruntimeError
}

// Code gets the status code for the pipeline service get template default response
func (o *PipelineServiceGetTemplateDefault) Code() int {
	return o._statusCode
}

func (o *PipelineServiceGetTemplateDefault) Error() string {
	return fmt.Sprintf("[GET /apis/v1beta1/pipelines/{id}/templates][%d] PipelineService_GetTemplate default  %+v", o._statusCode, o.Payload)
}

func (o *PipelineServiceGetTemplateDefault) readResponse(response runtime.ClientResponse, consumer runtime.Consumer, formats strfmt.Registry) error {

	o.Payload = new(pipeline_model.GatewayruntimeError)

	// response payload
	if err := consumer.Consume(response.Body(), o.Payload); err != nil && err != io.EOF {
		return err
	}

	return nil
}
