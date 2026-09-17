# -*- coding: utf-8 -*-
"""
Unit tests for per-tool audio volume attenuation, disk caching, and configuration integration.
"""

import os
import unittest
import wave
import array
from unittest.mock import patch, MagicMock

from utils.audio_player import get_volume_adjusted_wav, play_sound_with_volume
from modules.gamepad.sounds import play_gamepad_sound, get_gamepad_sound_asset_path
from modules.pomodoro.sounds import play_pomodoro_sound, get_sound_asset_path


class TestAudioVolume(unittest.TestCase):

    def setUp(self):
        self.test_assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sounds")
        self.sample_wav = os.path.join(self.test_assets_dir, "gamepad_click.wav")
        self.assertTrue(os.path.exists(self.sample_wav), "Base asset gamepad_click.wav must exist for volume tests")

    def test_volume_zero_is_silent(self):
        """Volume <= 0 should return None (mute)."""
        res0 = get_volume_adjusted_wav(self.sample_wav, 0)
        self.assertIsNone(res0)
        res_neg = get_volume_adjusted_wav(self.sample_wav, -10)
        self.assertIsNone(res_neg)

    def test_volume_hundred_returns_original(self):
        """Volume >= 100 should return the exact original path without modification."""
        res100 = get_volume_adjusted_wav(self.sample_wav, 100)
        self.assertEqual(res100, self.sample_wav)
        res150 = get_volume_adjusted_wav(self.sample_wav, 150)
        self.assertEqual(res150, self.sample_wav)

    def test_attenuated_wav_scaling_and_cache(self):
        """Volume between 1 and 99 should generate and cache a valid WAV file with reduced amplitude."""
        vol = 50
        res = get_volume_adjusted_wav(self.sample_wav, vol)
        self.assertIsNotNone(res)
        self.assertTrue(os.path.exists(res))
        self.assertTrue(res.endswith(f"_v{vol}.wav"))

        # Check sample amplitude reduction
        with wave.open(self.sample_wav, "rb") as wf_orig:
            orig_frames = wf_orig.readframes(wf_orig.getnframes())
            orig_samples = array.array("h", orig_frames)

        with wave.open(res, "rb") as wf_att:
            att_frames = wf_att.readframes(wf_att.getnframes())
            att_samples = array.array("h", att_frames)

        self.assertEqual(len(orig_samples), len(att_samples))
        # Samples should be roughly halved (50% amplitude)
        for i in range(min(50, len(orig_samples))):
            expected = int(orig_samples[i] * 0.5)
            self.assertEqual(att_samples[i], expected)

        # Second call should hit cache directly
        mtime_before = os.path.getmtime(res)
        res_cached = get_volume_adjusted_wav(self.sample_wav, vol)
        self.assertEqual(res, res_cached)
        self.assertEqual(os.path.getmtime(res_cached), mtime_before)

    @patch("utils.audio_player.sys.platform", "win32")
    def test_play_sound_with_volume_zero_skips_playback(self):
        """When volume is 0, no sound playback or winsound should be triggered."""
        with patch("winsound.PlaySound") as mock_play:
            play_sound_with_volume(self.sample_wav, volume=0)
            mock_play.assert_not_called()

    @patch("utils.audio_player.sys.platform", "win32")
    def test_play_sound_with_volume_windows_winsound(self):
        """On Windows, play_sound_with_volume should call winsound.PlaySound with attenuated file."""
        with patch("winsound.PlaySound") as mock_play:
            play_sound_with_volume(self.sample_wav, volume=60)
            mock_play.assert_called_once()
            called_path = mock_play.call_args[0][0]
            self.assertTrue(called_path.endswith("_v60.wav"))
            self.assertTrue(os.path.exists(called_path))

    @patch("modules.gamepad.sounds.play_sound_with_volume")
    def test_play_gamepad_sound_volume_passthrough(self, mock_play):
        """play_gamepad_sound should respect explicit volume and config volume."""
        with patch("modules.gamepad.sounds.get_module_config") as mock_cfg:
            mock_cfg.return_value = {
                "audio_feedback": True,
                "sound_preset": "click",
                "sound_volume": 45,
            }
            # 1. Config volume
            play_gamepad_sound()
            mock_play.assert_called_once()
            self.assertEqual(mock_play.call_args[1]["volume"], 45)

            # 2. Explicit volume override
            mock_play.reset_mock()
            play_gamepad_sound(volume=25)
            mock_play.assert_called_once()
            self.assertEqual(mock_play.call_args[1]["volume"], 25)

    @patch("modules.pomodoro.sounds.play_sound_with_volume")
    def test_play_pomodoro_sound_per_event_volume(self, mock_play):
        """Pomodoro sounds should resolve independent volumes for work, break, and alarm."""
        with patch("modules.pomodoro.sounds.get_module_config") as mock_cfg:
            mock_cfg.return_value = {
                "sound_notifications": True,
                "sound_preset": "bell",
                "sound_volume": 70,
                "break_sound_preset": "school_bell",
                "break_sound_volume": 40,
                "alarm_sound_preset": "digital_alarm",
                "alarm_sound_volume": 95,
            }

            # 1. Work sound volume
            play_pomodoro_sound(event_type="work_end")
            self.assertEqual(mock_play.call_args[1]["volume"], 70)

            # 2. Break sound volume
            mock_play.reset_mock()
            play_pomodoro_sound(event_type="break_end")
            self.assertEqual(mock_play.call_args[1]["volume"], 40)

            # 3. Focus loss alarm volume
            mock_play.reset_mock()
            play_pomodoro_sound(event_type="focus_loss")
            self.assertEqual(mock_play.call_args[1]["volume"], 95)

            # 4. Inactivity alarm volume
            mock_play.reset_mock()
            play_pomodoro_sound(event_type="inactivity")
            self.assertEqual(mock_play.call_args[1]["volume"], 95)


if __name__ == "__main__":
    unittest.main()
