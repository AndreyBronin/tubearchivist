"""test video segment timecode parsing"""

import pytest
from video.src.video_cut import TimecodeParseError, VideoClipper


class TestParseTimecode:
    """test VideoClipper.parse_timecode"""

    def test_seconds_only(self):
        assert VideoClipper.parse_timecode("90") == 90.0

    def test_mm_ss(self):
        assert VideoClipper.parse_timecode("01:25") == 85.0

    def test_hh_mm_ss(self):
        assert VideoClipper.parse_timecode("01:30:00") == 5400.0

    def test_mm_ss_ms_large(self):
        # third part is milliseconds: 00:15:500 -> 15.5s
        result = VideoClipper.parse_timecode("00:15:500")
        assert result == pytest.approx(15.5)

    def test_mm_ss_ms_small(self):
        # 18:10:01 -> 18 min 10 sec 1 ms = 1090.001s
        result = VideoClipper.parse_timecode("18:10:01")
        assert result == pytest.approx(18 * 60 + 10 + 1 / 1000.0)

    def test_mm_ss_ms_user_example(self):
        # from the user's example: 16:21-18:10:01
        # end timecode 18:10:01 -> 18*60 + 10 + 1/1000 = 1090.001s
        end = VideoClipper.parse_timecode("18:10:01")
        assert end == pytest.approx(1090.001)

    def test_with_spaces(self):
        assert VideoClipper.parse_timecode("  01:30  ") == 90.0

    def test_invalid_raises(self):
        with pytest.raises(TimecodeParseError):
            VideoClipper.parse_timecode("abc")


class TestParseSegments:
    """test VideoClipper.parse_segments"""

    def test_single_segment(self):
        result = VideoClipper.parse_segments("00:15-01:25")
        assert len(result) == 1
        assert result[0] == pytest.approx((15.0, 85.0))

    def test_multiple_segments(self):
        result = VideoClipper.parse_segments("00:15-01:25,16:21-18:10")
        assert len(result) == 2
        assert result[0] == pytest.approx((15.0, 85.0))
        # 16:21 = 981s, 18:10 = 1090s
        assert result[1] == pytest.approx((981.0, 1090.0))

    def test_user_example(self):
        # from the user's example: 00:15-01:25,16:21-18:10:01
        result = VideoClipper.parse_segments("00:15-01:25,16:21-18:10:01")
        assert len(result) == 2
        assert result[0] == pytest.approx((15.0, 85.0))
        # 16:21 = 981s, 18:10:01 = 1090.001s
        assert result[1][0] == pytest.approx(981.0)
        assert result[1][1] == pytest.approx(1090.001)

    def test_ignores_blank_parts(self):
        result = VideoClipper.parse_segments("00:15-01:25,")
        assert len(result) == 1

    def test_end_before_start_raises(self):
        with pytest.raises(TimecodeParseError):
            VideoClipper.parse_segments("01:25-00:15")

    def test_missing_separator_raises(self):
        with pytest.raises(TimecodeParseError):
            VideoClipper.parse_segments("00:15")

    def test_empty_string_raises(self):
        with pytest.raises(TimecodeParseError):
            VideoClipper.parse_segments("")

    def test_with_milliseconds(self):
        # 00:15:500 -> 15.5s, 01:10:250 -> 70.25s
        result = VideoClipper.parse_segments("00:15:500-01:10:250")
        assert len(result) == 1
        start, end = result[0]
        assert start == pytest.approx(15.5)
        assert end == pytest.approx(70.25)
