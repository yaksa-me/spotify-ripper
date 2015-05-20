# -*- coding: utf8 -*-

from __future__ import unicode_literals

from colorama import Cursor
from spotify_ripper.utils import *
import os, sys
import time
import schedule

class Progress(object):

    # song progress
    current_track = None
    song_position = 0
    song_duration = 0

    # total progress
    show_total = False
    total_position = 0
    total_duration = 0

    # eta calculations
    stat_prev = None
    song_eta = None
    total_eta = None

    # flag for moving cursor
    move_cursor = False

    def __init__(self, args, ripper):
        self.args = args
        self.ripper = ripper
        if not self.args.has_log:
            schedule.every(2).seconds.do(self.eta_calc)

    def calc_total(self, tracks):
        if len(tracks) <= 1:
            return

        self.show_total = True
        self.total_duration = 0

        # some duplicate work here, maybe cache this info beforehand?
        for idx, track in enumerate(tracks):
            track.load()
            if track.availability != 1: continue
            mp3_file = self.ripper.track_path(idx, track)
            if not self.args.overwrite and os.path.exists(mp3_file): continue
            self.total_duration += track.duration

    def eta_calc(self):
        def calc(pos, dur, rate, old_eta):
            new_eta = (dur - pos) / rate
            # debounce and round
            if old_eta is None or abs(new_eta - old_eta) > 10:
                r = new_eta % 15
                new_eta += ((15 - r) if r >= 7 else (0 - r))
                return new_eta
            return old_eta

        if self.ripper.ripping:
            if self.stat_prev is not None:
                rate = (self.song_position - self.stat_prev[0]) / (time.time() - self.stat_prev[1])
                if rate > 0.00000001:

                    # calc song eta
                    self.song_eta = calc(self.song_position, self.song_duration, rate, self.song_eta)

                    # calc total eta
                    if self.show_total:
                        total_position = (self.total_position + self.song_position)
                        self.total_eta = calc(total_position, self.total_duration, rate, self.total_eta)

            self.stat_prev = (self.song_position, time.time())

    def prepare_track(self, track):
        self.song_position = 0
        self.song_duration = track.duration
        self.move_cursor = False
        self.current_track = track

    def end_track(self):
        self.stat_prev = None
        self.song_eta = None
        self.total_eta = None
        self.total_position += self.current_track.duration
        self.current_track = None
        self.end_progress()

    def update_progress(self, num_frames, audio_format):
        if self.args.has_log: return

        self.song_position += (num_frames * 1000) / audio_format.sample_rate
        pos_seconds = self.song_position // 1000
        dur_seconds = self.song_duration // 1000
        pct = int(self.song_position * 100 // self.song_duration)
        x = int(pct * 40 // 100)

        # don't move cursor on first update
        if self.show_total:
            if self.move_cursor:
                print(Cursor.UP(2))
            else:
                self.move_cursor = True

        print_str(self.args, "\rProgress: [" + ("=" * x) + (" " * (40 - x)) + "] " + format_time(pos_seconds, dur_seconds))
        if self.song_eta is not None:
            print_str(self.args, ("\t(~" + format_time(self.song_eta, short=True) + " remaining)"))

        if self.show_total:
            total_position = self.total_position + self.song_position
            total_pos_seconds = total_position // 1000
            total_dur_seconds = self.total_duration // 1000
            total_pct = int(total_position * 100 // self.total_duration)
            total_x = int(total_pct * 40 // 100)
            print_str(self.args, "\nTotal:    [" + ("=" * total_x) + (" " * (40 - total_x)) + "] " + format_time(total_pos_seconds, total_dur_seconds))
            if self.total_eta is not None:
                print_str(self.args, ("\t(~" + format_time(self.total_eta, short=True) + " remaining)"))

    def end_progress(self):
        print_str(self.args, "\n")