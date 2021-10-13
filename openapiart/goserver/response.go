// This file is autogenerated. Do not modify
package httpapi

import (
	"encoding/json"
	"fmt"
	"net/http"
)

// JSONWriter offers conversion to JSON.
type JSONWriter interface {
	ToJson() string
}

// WriteJSONResponse sets an HTTP response with the provided status-code and JSON body.
func WriteJSONResponse(w http.ResponseWriter, statuscode int, data JSONWriter) (int, error) {
	w.WriteHeader(statuscode)
	w.Header().Set("Content-Type", "application/json; charset=UTF-8")
	return w.Write([]byte(data.ToJson()))
}

// WriteTextResponse sets an HTTP response with the provided status-code and string.
func WriteAnyResponse(w http.ResponseWriter, statuscode int, data interface{}) (int, error) {
	w.WriteHeader(statuscode)
	w.Header().Set("Content-Type", "text/plain; charset=UTF-8")
	var dataBytes, _ = json.Marshal(data)
	return w.Write(dataBytes)
}

// YAMLWriter offers conversion to YAML.
type YAMLWriter interface {
	ToYaml() string
}

// WriteYAMLResponse sets an HTTP response with the provided status-code and JSON body.
func WriteYAMLResponse(w http.ResponseWriter, statuscode int, data YAMLWriter) (int, error) {
	w.WriteHeader(statuscode)
	w.Header().Set("Content-Type", "application/yaml; charset=UTF-8")
	return w.Write([]byte(data.ToYaml()))
}

// WriteDefaultResponse sets the body of a response with the text associated with the HTTP status.
func WriteDefaultResponse(w http.ResponseWriter, status int) (int, error) {
	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.WriteHeader(status)
	fmt.Fprintf(w, "%d %s", status, http.StatusText(status))
	return status, nil
}
