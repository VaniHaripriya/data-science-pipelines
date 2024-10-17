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

// PipelineServiceCreatePipelineVersionV1Reader is a Reader for the PipelineServiceCreatePipelineVersionV1 structure.
type PipelineServiceCreatePipelineVersionV1Reader struct {
	formats strfmt.Registry
}

// ReadResponse reads a server response into the received o.
func (o *PipelineServiceCreatePipelineVersionV1Reader) ReadResponse(response runtime.ClientResponse, consumer runtime.Consumer) (interface{}, error) {
	switch response.Code() {

	case 200:
		result := NewPipelineServiceCreatePipelineVersionV1OK()
		if err := result.readResponse(response, consumer, o.formats); err != nil {
			return nil, err
		}
		return result, nil

	default:
		result := NewPipelineServiceCreatePipelineVersionV1Default(response.Code())
		if err := result.readResponse(response, consumer, o.formats); err != nil {
			return nil, err
		}
		if response.Code()/100 == 2 {
			return result, nil
		}
		return nil, result
	}
}

// NewPipelineServiceCreatePipelineVersionV1OK creates a PipelineServiceCreatePipelineVersionV1OK with default headers values
func NewPipelineServiceCreatePipelineVersionV1OK() *PipelineServiceCreatePipelineVersionV1OK {
	return &PipelineServiceCreatePipelineVersionV1OK{}
}

/*PipelineServiceCreatePipelineVersionV1OK handles this case with default header values.

A successful response.
*/
type PipelineServiceCreatePipelineVersionV1OK struct {
	Payload *pipeline_model.APIPipelineVersion
}

func (o *PipelineServiceCreatePipelineVersionV1OK) Error() string {
	return fmt.Sprintf("[POST /apis/v1beta1/pipeline_versions][%d] pipelineServiceCreatePipelineVersionV1OK  %+v", 200, o.Payload)
}

func (o *PipelineServiceCreatePipelineVersionV1OK) readResponse(response runtime.ClientResponse, consumer runtime.Consumer, formats strfmt.Registry) error {

	o.Payload = new(pipeline_model.APIPipelineVersion)

	// response payload
	if err := consumer.Consume(response.Body(), o.Payload); err != nil && err != io.EOF {
		return err
	}

	return nil
}

// NewPipelineServiceCreatePipelineVersionV1Default creates a PipelineServiceCreatePipelineVersionV1Default with default headers values
func NewPipelineServiceCreatePipelineVersionV1Default(code int) *PipelineServiceCreatePipelineVersionV1Default {
	return &PipelineServiceCreatePipelineVersionV1Default{
		_statusCode: code,
	}
}

/*PipelineServiceCreatePipelineVersionV1Default handles this case with default header values.

An unexpected error response.
*/
type PipelineServiceCreatePipelineVersionV1Default struct {
	_statusCode int

	Payload *pipeline_model.GatewayruntimeError
}

// Code gets the status code for the pipeline service create pipeline version v1 default response
func (o *PipelineServiceCreatePipelineVersionV1Default) Code() int {
	return o._statusCode
}

func (o *PipelineServiceCreatePipelineVersionV1Default) Error() string {
	return fmt.Sprintf("[POST /apis/v1beta1/pipeline_versions][%d] PipelineService_CreatePipelineVersionV1 default  %+v", o._statusCode, o.Payload)
}

func (o *PipelineServiceCreatePipelineVersionV1Default) readResponse(response runtime.ClientResponse, consumer runtime.Consumer, formats strfmt.Registry) error {

	o.Payload = new(pipeline_model.GatewayruntimeError)

	// response payload
	if err := consumer.Consume(response.Body(), o.Payload); err != nil && err != io.EOF {
		return err
	}

	return nil
}
