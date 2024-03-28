// Code generated by go-swagger; DO NOT EDIT.

package pipeline_service

// This file was generated by the swagger tool.
// Editing this file might prove futile when you re-run the swagger generate command

import (
	"fmt"
	"io"

	"github.com/go-openapi/runtime"

	strfmt "github.com/go-openapi/strfmt"

	pipeline_model "github.com/kubeflow/pipelines/backend/api/v2beta1/go_http_client/pipeline_model"
)

// PipelineServiceDeletePipelineReader is a Reader for the PipelineServiceDeletePipeline structure.
type PipelineServiceDeletePipelineReader struct {
	formats strfmt.Registry
}

// ReadResponse reads a server response into the received o.
func (o *PipelineServiceDeletePipelineReader) ReadResponse(response runtime.ClientResponse, consumer runtime.Consumer) (interface{}, error) {
	switch response.Code() {

	case 200:
		result := NewPipelineServiceDeletePipelineOK()
		if err := result.readResponse(response, consumer, o.formats); err != nil {
			return nil, err
		}
		return result, nil

	default:
		result := NewPipelineServiceDeletePipelineDefault(response.Code())
		if err := result.readResponse(response, consumer, o.formats); err != nil {
			return nil, err
		}
		if response.Code()/100 == 2 {
			return result, nil
		}
		return nil, result
	}
}

// NewPipelineServiceDeletePipelineOK creates a PipelineServiceDeletePipelineOK with default headers values
func NewPipelineServiceDeletePipelineOK() *PipelineServiceDeletePipelineOK {
	return &PipelineServiceDeletePipelineOK{}
}

/*PipelineServiceDeletePipelineOK handles this case with default header values.

A successful response.
*/
type PipelineServiceDeletePipelineOK struct {
	Payload interface{}
}

func (o *PipelineServiceDeletePipelineOK) Error() string {
	return fmt.Sprintf("[DELETE /apis/v2beta1/pipelines/{pipeline_id}][%d] pipelineServiceDeletePipelineOK  %+v", 200, o.Payload)
}

func (o *PipelineServiceDeletePipelineOK) readResponse(response runtime.ClientResponse, consumer runtime.Consumer, formats strfmt.Registry) error {

	// response payload
	if err := consumer.Consume(response.Body(), &o.Payload); err != nil && err != io.EOF {
		return err
	}

	return nil
}

// NewPipelineServiceDeletePipelineDefault creates a PipelineServiceDeletePipelineDefault with default headers values
func NewPipelineServiceDeletePipelineDefault(code int) *PipelineServiceDeletePipelineDefault {
	return &PipelineServiceDeletePipelineDefault{
		_statusCode: code,
	}
}

/*PipelineServiceDeletePipelineDefault handles this case with default header values.

An unexpected error response.
*/
type PipelineServiceDeletePipelineDefault struct {
	_statusCode int

	Payload *pipeline_model.RuntimeError
}

// Code gets the status code for the pipeline service delete pipeline default response
func (o *PipelineServiceDeletePipelineDefault) Code() int {
	return o._statusCode
}

func (o *PipelineServiceDeletePipelineDefault) Error() string {
	return fmt.Sprintf("[DELETE /apis/v2beta1/pipelines/{pipeline_id}][%d] PipelineService_DeletePipeline default  %+v", o._statusCode, o.Payload)
}

func (o *PipelineServiceDeletePipelineDefault) readResponse(response runtime.ClientResponse, consumer runtime.Consumer, formats strfmt.Registry) error {

	o.Payload = new(pipeline_model.RuntimeError)

	// response payload
	if err := consumer.Consume(response.Body(), o.Payload); err != nil && err != io.EOF {
		return err
	}

	return nil
}