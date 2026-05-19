package jsonutil

import (
	"bytes"
	"encoding/json"
)

// UnmarshalStrict unmarshals JSON data into v and rejects any unknown fields
// that are not present in v's type definition.
func UnmarshalStrict(data []byte, v any) error {
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.DisallowUnknownFields()
	return dec.Decode(v)
}
