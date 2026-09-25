import unittest

from dnsfmt.records import (
    DNSRecord,
    ZoneSyntaxError,
    format_record,
    normalize_rdata,
    parse_line,
)


class ParseLineTTLAndClassOrdering(unittest.TestCase):
    def test_ttl_before_class(self):
        record, _ = parse_line("example.com. 3600 IN A 203.0.113.10", None, 300)
        self.assertEqual(record.ttl, 3600)
        self.assertEqual(record.rec_class, "IN")

    def test_class_before_ttl(self):
        record, _ = parse_line("example.com. IN 3600 A 203.0.113.10", None, 300)
        self.assertEqual(record.ttl, 3600)
        self.assertEqual(record.rec_class, "IN")

    def test_ttl_only_defaults_class_to_in(self):
        record, _ = parse_line("example.com. 3600 A 203.0.113.10", None, 300)
        self.assertEqual(record.ttl, 3600)
        self.assertEqual(record.rec_class, "IN")

    def test_class_only_falls_back_to_default_ttl(self):
        record, _ = parse_line("example.com. IN A 203.0.113.10", None, 7200)
        self.assertEqual(record.ttl, 7200)
        self.assertEqual(record.rec_class, "IN")

    def test_neither_ttl_nor_class_uses_default_ttl_and_in(self):
        record, _ = parse_line("example.com. A 203.0.113.10", None, 300)
        self.assertEqual(record.ttl, 300)
        self.assertEqual(record.rec_class, "IN")

    def test_chaos_class_is_preserved(self):
        record, _ = parse_line("example.com. CH TXT hello", None, 300)
        self.assertEqual(record.rec_class, "CH")


class ParseLineNameInheritance(unittest.TestCase):
    def test_indented_line_reuses_previous_name(self):
        first, last_name = parse_line("www 3600 IN A 203.0.113.10", None, 300)
        self.assertEqual(last_name, "www")

        second, last_name = parse_line("  3600 IN A 198.51.100.7", last_name, 300)
        self.assertEqual(second.name, "www.")
        self.assertEqual(last_name, "www")

    def test_indentation_with_tab_also_inherits(self):
        _, last_name = parse_line("www 3600 IN A 203.0.113.10", None, 300)
        record, _ = parse_line("\tIN MX 10 mail-relay", last_name, 300)
        self.assertEqual(record.name, "www.")

    def test_missing_name_with_no_prior_record_raises(self):
        with self.assertRaises(ZoneSyntaxError):
            parse_line("  IN A 203.0.113.10", None, 300)

    def test_at_sign_is_left_as_is(self):
        record, last_name = parse_line("@ 3600 IN A 203.0.113.10", None, 300)
        self.assertEqual(record.name, "@")
        self.assertEqual(last_name, "@")


class ParseLineMalformedInput(unittest.TestCase):
    def test_blank_line_returns_none_and_keeps_last_name(self):
        record, last_name = parse_line("   ", "www", 300)
        self.assertIsNone(record)
        self.assertEqual(last_name, "www")

    def test_comment_only_line_returns_none(self):
        record, last_name = parse_line("; a note", "www", 300)
        self.assertIsNone(record)
        self.assertEqual(last_name, "www")

    def test_name_with_nothing_after_it_raises(self):
        with self.assertRaises(ZoneSyntaxError):
            parse_line("example.com.", None, 300)

    def test_ttl_and_class_but_no_type_raises(self):
        with self.assertRaises(ZoneSyntaxError):
            parse_line("example.com. 3600 IN", None, 300)

    def test_type_with_no_rdata_raises(self):
        with self.assertRaises(ZoneSyntaxError):
            parse_line("example.com. A", None, 300)


class NormalizeRdataTests(unittest.TestCase):
    def test_hostname_rdata_gets_qualified(self):
        self.assertEqual(normalize_rdata("CNAME", ["example.com"]), "example.com.")
        self.assertEqual(normalize_rdata("NS", ["ns1.example.com."]), "ns1.example.com.")

    def test_mx_qualifies_only_the_hostname(self):
        self.assertEqual(normalize_rdata("MX", ["10", "mail-relay"]), "10 mail-relay.")

    def test_soa_qualifies_mname_and_rname(self):
        rdata = normalize_rdata(
            "SOA",
            ["ns1.example.com", "hostmaster.example.com", "1", "3600", "900", "604800", "86400"],
        )
        self.assertEqual(
            rdata, "ns1.example.com. hostmaster.example.com. 1 3600 900 604800 86400"
        )

    def test_srv_qualifies_only_the_target(self):
        self.assertEqual(
            normalize_rdata("SRV", ["10", "20", "5060", "sipserver"]), "10 20 5060 sipserver."
        )

    def test_unrecognized_shape_passes_through_unchanged(self):
        self.assertEqual(normalize_rdata("TXT", ["hello", "world"]), "hello world")


class FormatRecordTests(unittest.TestCase):
    def test_fields_are_left_justified_and_space_separated(self):
        record = DNSRecord(
            name="example.com.", ttl=3600, rec_class="IN", rtype="A", rdata="203.0.113.10"
        )
        expected = (
            "example.com.".ljust(24)
            + " "
            + "3600".ljust(6)
            + " "
            + "IN".ljust(3)
            + " "
            + "A".ljust(6)
            + " "
            + "203.0.113.10"
        )
        self.assertEqual(format_record(record), expected)

    def test_custom_widths_are_honored(self):
        record = DNSRecord(name="a.", ttl=60, rec_class="IN", rtype="A", rdata="1.2.3.4")
        formatted = format_record(record, name_width=10, ttl_width=4)
        expected = (
            "a.".ljust(10) + " " + "60".ljust(4) + " " + "IN".ljust(3) + " " + "A".ljust(6) + " " + "1.2.3.4"
        )
        self.assertEqual(formatted, expected)


if __name__ == "__main__":
    unittest.main()
