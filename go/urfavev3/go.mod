module murli-work-urfavev3

go 1.26.2

require (
	github.com/allank/murli v1.0.2
	github.com/urfave/cli/v3 v3.9.0
	murli-work-shared v0.0.0
)

replace murli-work-shared => ../shared

replace github.com/allank/murli => github.com/murli-cli/murli-go v1.0.2
