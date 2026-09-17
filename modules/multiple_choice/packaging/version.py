# -*- coding: utf-8 -*-
import re

class Version:
    def __init__(self, vstring):
        self.vstring = vstring
        parts = [int(p) for p in re.findall(r"\d+", vstring)]
        self.parts = tuple(parts)

    def __lt__(self, other):
        return self.parts < other.parts

    def __le__(self, other):
        return self.parts <= other.parts

    def __gt__(self, other):
        return self.parts > other.parts

    def __ge__(self, other):
        return self.parts >= other.parts

    def __eq__(self, other):
        return self.parts == other.parts


def parse(vstring):
    return Version(vstring)
