module murli-work-cobra

go 1.26.2

require (
	github.com/allank/murli v1.0.2
	github.com/spf13/cobra v1.8.0
	murli-work-shared v0.0.0
)

require (
	github.com/inconshreveable/mousetrap v1.1.0 // indirect
	github.com/spf13/pflag v1.0.5 // indirect
)

replace murli-work-shared => ../shared

replace github.com/allank/murli => github.com/murli-cli/murli-go v1.0.2
