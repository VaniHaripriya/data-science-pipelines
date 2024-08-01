// Code generated by go-swagger; DO NOT EDIT.

package run_service

// This file was generated by the swagger tool.
// Editing this file might prove futile when you re-run the swagger generate command

import (
	"fmt"
	"io"

	"github.com/go-openapi/runtime"

	strfmt "github.com/go-openapi/strfmt"

	run_model "github.com/kubeflow/pipelines/backend/api/v1beta1/go_http_client/run_model"
)

// RunServiceUnarchiveRunV1Reader is a Reader for the RunServiceUnarchiveRunV1 structure.
type RunServiceUnarchiveRunV1Reader struct {
	formats strfmt.Registry
}

// ReadResponse reads a server response into the received o.
func (o *RunServiceUnarchiveRunV1Reader) ReadResponse(response runtime.ClientResponse, consumer runtime.Consumer) (interface{}, error) {
	switch response.Code() {

	case 200:
		result := NewRunServiceUnarchiveRunV1OK()
		if err := result.readResponse(response, consumer, o.formats); err != nil {
			return nil, err
		}
		return result, nil

	default:
		result := NewRunServiceUnarchiveRunV1Default(response.Code())
		if err := result.readResponse(response, consumer, o.formats); err != nil {
			return nil, err
		}
		if response.Code()/100 == 2 {
			return result, nil
		}
		return nil, result
	}
}

// NewRunServiceUnarchiveRunV1OK creates a RunServiceUnarchiveRunV1OK with default headers values
func NewRunServiceUnarchiveRunV1OK() *RunServiceUnarchiveRunV1OK {
	return &RunServiceUnarchiveRunV1OK{}
}

/*RunServiceUnarchiveRunV1OK handles this case with default header values.

A successful response.
*/
type RunServiceUnarchiveRunV1OK struct {
	Payload interface{}
}

func (o *RunServiceUnarchiveRunV1OK) Error() string {
	return fmt.Sprintf("[POST /apis/v1beta1/runs/{id}:unarchive][%d] runServiceUnarchiveRunV1OK  %+v", 200, o.Payload)
}

func (o *RunServiceUnarchiveRunV1OK) readResponse(response runtime.ClientResponse, consumer runtime.Consumer, formats strfmt.Registry) error {

	// response payload
	if err := consumer.Consume(response.Body(), &o.Payload); err != nil && err != io.EOF {
		return err
	}

	return nil
}

// NewRunServiceUnarchiveRunV1Default creates a RunServiceUnarchiveRunV1Default with default headers values
func NewRunServiceUnarchiveRunV1Default(code int) *RunServiceUnarchiveRunV1Default {
	return &RunServiceUnarchiveRunV1Default{
		_statusCode: code,
	}
}

/*RunServiceUnarchiveRunV1Default handles this case with default header values.

An unexpected error response.
*/
type RunServiceUnarchiveRunV1Default struct {
	_statusCode int

	Payload *run_model.GatewayruntimeError
}

// Code gets the status code for the run service unarchive run v1 default response
func (o *RunServiceUnarchiveRunV1Default) Code() int {
	return o._statusCode
}

func (o *RunServiceUnarchiveRunV1Default) Error() string {
	return fmt.Sprintf("[POST /apis/v1beta1/runs/{id}:unarchive][%d] RunService_UnarchiveRunV1 default  %+v", o._statusCode, o.Payload)
}

func (o *RunServiceUnarchiveRunV1Default) readResponse(response runtime.ClientResponse, consumer runtime.Consumer, formats strfmt.Registry) error {

	o.Payload = new(run_model.GatewayruntimeError)

	// response payload
	if err := consumer.Consume(response.Body(), o.Payload); err != nil && err != io.EOF {
		return err
	}

	return nil
}
