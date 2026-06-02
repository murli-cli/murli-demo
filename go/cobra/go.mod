module murli-work-cobra

go 1.26.2

require (
	github.com/murli-cli/murli-go v1.0.3-0.20260602052039-7ed6903a78a5
	github.com/spf13/cobra v1.8.0
	murli-work-shared v0.0.0
)

require (
	github.com/inconshreveable/mousetrap v1.1.0 // indirect
	github.com/spf13/pflag v1.0.5 // indirect
)

replace murli-work-shared => ../shared
