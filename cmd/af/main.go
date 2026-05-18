package main

import (
	"flag"
	"fmt"
	"os"

	"github.com/agent-fox/af/internal/version"
)

func main() {
	showVersion := flag.Bool("version", false, "print version and exit")
	flag.Parse()

	if *showVersion {
		fmt.Println(version.String())
		return
	}

	fmt.Fprintf(os.Stderr, "af %s — agent-fox next version\n", version.String())
	os.Exit(0)
}
