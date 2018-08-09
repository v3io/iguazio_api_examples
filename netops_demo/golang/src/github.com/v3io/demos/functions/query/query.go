package query

import (
	"github.com/nuclio/nuclio-sdk-go"
)

func Query(context *nuclio.Context, event nuclio.Event) (interface{}, error) {
	context.Logger.InfoWith("Querying")

	return nil, nil
}

// InitContext runs only once when the function runtime starts
func InitContext(context *nuclio.Context) error {
	context.Logger.InfoWith("Initializing")

	return nil
}
