package main

import (
	"os"

	"github.com/v3io/demos/functions/ingest"

	"github.com/nuclio/nuclio-sdk-go"
)

func Ingest(context *nuclio.Context, event nuclio.Event) (interface{}, error) {
	return ingest.Ingest(context, event)
}

// InitContext runs only once when the function runtime starts
func InitContext(context *nuclio.Context) error {
	switch os.Getenv("NUCLIO_HANDLER") {
	case "main:Ingest":
		return ingest.InitContext(context)
	}

	return nil
}
