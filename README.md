# dns-zone-formatter

Zone files that have been hand-edited for a while tend to rot: tabs mixed
with spaces, TTL and class in whatever order someone typed them that day,
some hostnames fully qualified and others not, blank lines everywhere.
`dnsfmt` reads records like that and prints them back out in one consistent,
aligned form.

It does not validate DNS semantics (it won't tell you an MX record is
missing a priority you forgot) - it just normalizes syntax so a zone file
is readable and diffable.

## Example

Input (`zone.txt`):

```
example.com.	IN	A	203.0.113.10
www 3600 IN CNAME example.com
	  A    198.51.100.7
mail.example.com IN MX 10 mail-relay
```

```
$ dnsfmt zone.txt
example.com.             3600   IN  A      203.0.113.10
www.                     3600   IN  CNAME  example.com.
www.                     3600   IN  A      198.51.100.7
mail.example.com.        3600   IN  MX     10 mail-relay.
```

Notes on what changed: mixed tabs/spaces collapsed to single spaces between
aligned columns, TTL defaulted in wherever it was missing, bare hostnames
got a trailing dot, and the indented line inherited `www` as its owner name
per standard zone file shorthand.

## Usage

From a file:

```
dnsfmt zone.txt
```

From stdin (also the default with no arguments):

```
cat zone.txt | dnsfmt
dig +nocmd example.com A +noall +answer | dnsfmt
```

Multiple files are concatenated in order:

```
dnsfmt zone1.txt zone2.txt
```

Override the default TTL applied to records that omit one (default 3600):

```
dnsfmt --default-ttl 86400 zone.txt
```

Malformed lines are reported to stderr with a line number and skipped; the
rest of the input is still processed. The exit code is non-zero if any line
failed to parse.

## Supported input

- `name [ttl] [class] type rdata` in any order for `ttl`/`class`, both optional
- indented lines that omit the name, reusing the previous record's owner
- `;` comments, including safely inside quoted TXT strings
- any record type; `CNAME`, `NS`, `PTR`, the hostname field of `MX`, the
  mname/rname fields of `SOA`, and the target field of `SRV` get a trailing
  dot added if missing, everything else is passed through as-is
- `SOA` and `SRV` records must fit on one line (no parenthesized
  multi-line rdata yet)

## Requirements

Python 3.9+, standard library only.

## Install

```
pip install -e .
```

This installs the `dnsfmt` command via the entry point in `pyproject.toml`.
