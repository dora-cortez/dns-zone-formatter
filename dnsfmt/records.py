"""Parsing and normalization for zone-file-style DNS records.

Grammar handled per line (BIND-style master file, simplified):

    [name] [ttl] [class] type rdata...

`name` is optional if the line starts with whitespace, in which case it
reuses the name of the previous record (the standard zone file shorthand
for grouping several records under one owner). `ttl` and `class` are each
optional and may appear in either order.
"""

from dataclasses import dataclass

CLASSES = {"IN", "CH", "HS"}

# Record types whose rdata contains a hostname that should be fully
# qualified (trailing dot) rather than left as free-form text.
HOSTNAME_RDATA = {"CNAME", "NS", "PTR"}


class ZoneSyntaxError(ValueError):
    pass


@dataclass
class DNSRecord:
    name: str
    ttl: int
    rec_class: str
    rtype: str
    rdata: str


def strip_comment(line):
    # ';' starts a comment unless it's inside a quoted string (TXT rdata
    # can legitimately contain one).
    out = []
    in_quotes = False
    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes
        if ch == ";" and not in_quotes:
            break
        out.append(ch)
    return "".join(out)


def fqdn(name):
    if name == "@" or name.endswith("."):
        return name
    return name + "."


def parse_line(raw_line, last_name, default_ttl):
    """Parse one input line.

    Returns (DNSRecord | None, new_last_name). Returns (None, last_name)
    for blank or comment-only lines. Raises ZoneSyntaxError on malformed
    records.
    """
    line = strip_comment(raw_line)
    if not line.strip():
        return None, last_name

    inherits_name = line[0] in (" ", "\t")
    tokens = line.split()
    idx = 0

    if inherits_name:
        if last_name is None:
            raise ZoneSyntaxError("record has no name and none precedes it")
        name = last_name
    else:
        name = tokens[idx]
        idx += 1

    if idx >= len(tokens):
        raise ZoneSyntaxError(f"incomplete record: {raw_line!r}")

    ttl = None
    rec_class = None
    while idx < len(tokens):
        tok = tokens[idx]
        if ttl is None and tok.isdigit():
            ttl = int(tok)
            idx += 1
            continue
        if rec_class is None and tok.upper() in CLASSES:
            rec_class = tok.upper()
            idx += 1
            continue
        break

    if idx >= len(tokens):
        raise ZoneSyntaxError(f"record has no type: {raw_line!r}")

    rtype = tokens[idx].upper()
    idx += 1

    rdata_tokens = tokens[idx:]
    if not rdata_tokens:
        raise ZoneSyntaxError(f"record has no rdata: {raw_line!r}")

    rdata = normalize_rdata(rtype, rdata_tokens)

    record = DNSRecord(
        name=fqdn(name),
        ttl=default_ttl if ttl is None else ttl,
        rec_class=rec_class or "IN",
        rtype=rtype,
        rdata=rdata,
    )
    return record, name


def normalize_rdata(rtype, rdata_tokens):
    if rtype in HOSTNAME_RDATA and len(rdata_tokens) == 1:
        return fqdn(rdata_tokens[0])
    if rtype == "MX" and len(rdata_tokens) == 2:
        priority, host = rdata_tokens
        return f"{priority} {fqdn(host)}"
    if rtype == "SOA" and len(rdata_tokens) == 7:
        # mname (primary nameserver) and rname (mailbox, dot instead of @)
        # are the only hostname-shaped fields; the rest are plain integers.
        mname, rname, *timers = rdata_tokens
        return f"{fqdn(mname)} {fqdn(rname)} " + " ".join(timers)
    if rtype == "SRV" and len(rdata_tokens) == 4:
        priority, weight, port, target = rdata_tokens
        return f"{priority} {weight} {port} {fqdn(target)}"
    return " ".join(rdata_tokens)


def format_record(record, name_width=24, ttl_width=6):
    return (
        f"{record.name:<{name_width}} "
        f"{record.ttl:<{ttl_width}} "
        f"{record.rec_class:<3} "
        f"{record.rtype:<6} "
        f"{record.rdata}"
    )
