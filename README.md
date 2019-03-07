# DMARC Forwarder

A tool for analysing and forwarding incoming DMARC-reports.


## Installation and dependencies

This program is written in Python 3 and only uses standard library features. In order to send emails, this tool needs access to an SMTP server. It assumes one is available on `localhost:25`.

The script can just be downloaded as-is and run using a python 3 interpreter.

## Usage

This tool reads an e-mail message from standard input (or optionally a file) and parses a DMARC-report for failures. When there are failures, it will forward the original DMARC-report along with a short summary to a specified email address. You can use the `--forward-passing` flag to always forward a summary even if the report does not contain failures.

For options, you can run `./dmarcforwarder.py --help`

You can use it from procmail with the following rule (assuming you have an email account configured that handles DMARC reports):

```procmail
:0
# Some rule that only matches DMARC reports
* ^To: dmarc@example.org
| /full/path/to/dmarcforwarder.py
```

## Contributing

Feel free to send me a pull-request or an issue if you have suggestions for improvement. This tool was written mainly for myself when I was experimenting with my own personal mail server and its DMARC set-up so that's what it can do right now.

## License

This software is licensed under the MIT license. If that doesn't work for you, feel free to contact me and we can probably work something out.
