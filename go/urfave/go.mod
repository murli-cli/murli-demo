module murli-work-urfave

go 1.26.2

require (
	github.com/murli-cli/murli-go v1.0.2
	github.com/urfave/cli/v2 v2.27.7
	murli-work-shared v0.0.0
)

require (
	github.com/cpuguy83/go-md2man/v2 v2.0.7 // indirect
	github.com/russross/blackfriday/v2 v2.1.0 // indirect
	github.com/xrash/smetrics v0.0.0-20240521201337-686a1a2994c1 // indirect
)

replace murli-work-shared => ../shared
