"""
SVG Path Parser - Parses SVG path strings into command arrays.

This module provides functionality equivalent to the parse-svg-path npm package.
"""

import re
from typing import Union


# SVG path command argument counts
# Each command type has a fixed number of numeric arguments
COMMAND_ARGS = {
    "M": 2,  # moveto: x, y
    "m": 2,
    "L": 2,  # lineto: x, y
    "l": 2,
    "H": 1,  # horizontal lineto: x
    "h": 1,
    "V": 1,  # vertical lineto: y
    "v": 1,
    "C": 6,  # curveto: x1, y1, x2, y2, x, y
    "c": 6,
    "S": 4,  # smooth curveto: x2, y2, x, y
    "s": 4,
    "Q": 4,  # quadratic curveto: x1, y1, x, y
    "q": 4,
    "T": 2,  # smooth quadratic curveto: x, y
    "t": 2,
    "A": 7,  # arc: rx, ry, x-axis-rotation, large-arc-flag, sweep-flag, x, y
    "a": 7,
    "Z": 0,  # closepath
    "z": 0,
}

# Regex to match numbers (integers and floats, positive and negative)
NUMBER_PATTERN = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")

# Regex to match command letters
COMMAND_PATTERN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]")


def parse(path: str) -> list[list[Union[str, float]]]:
    """
    Parse an SVG path string into a list of commands.

    Each command is represented as a list where:
    - The first element is the command letter (str)
    - Subsequent elements are the numeric parameters (float)

    Args:
        path: An SVG path string, e.g., "M0,0 L100,100 Z"

    Returns:
        A list of parsed commands, e.g., [['M', 0.0, 0.0], ['L', 100.0, 100.0], ['Z']]
    """
    commands: list[list[Union[str, float]]] = []

    # Tokenize: extract all commands and numbers
    tokens: list[Union[str, float]] = []
    pos = 0

    while pos < len(path):
        char = path[pos]

        # Skip whitespace and commas
        if char in " \t\n\r,":
            pos += 1
            continue

        # Check for command letter
        if COMMAND_PATTERN.match(char):
            tokens.append(char)
            pos += 1
            continue

        # Try to match a number
        match = NUMBER_PATTERN.match(path, pos)
        if match:
            tokens.append(float(match.group()))
            pos = match.end()
            continue

        # Unknown character, skip it
        pos += 1

    # Group tokens into commands
    i = 0
    while i < len(tokens):
        token = tokens[i]

        if isinstance(token, str) and token in COMMAND_ARGS:
            cmd = token
            num_args = COMMAND_ARGS[cmd]

            # Collect arguments for this command
            args: list[float] = []
            j = i + 1
            while len(args) < num_args and j < len(tokens):
                if isinstance(tokens[j], float):
                    args.append(tokens[j])
                    j += 1
                else:
                    break

            command: list[Union[str, float]] = [cmd] + args
            commands.append(command)
            i = j

            # Handle implicit commands (repeated coordinates for M become L, etc.)
            # M/m can have implicit L/l commands after the first coordinate pair
            if cmd in (
                "M",
                "m",
                "L",
                "l",
                "C",
                "c",
                "S",
                "s",
                "Q",
                "q",
                "T",
                "t",
                "A",
                "a",
            ):
                implicit_cmd = cmd
                if cmd == "M":
                    implicit_cmd = "L"
                elif cmd == "m":
                    implicit_cmd = "l"

                # Check for more numbers that form implicit commands
                while i < len(tokens) and isinstance(tokens[i], float):
                    implicit_args: list[float] = []
                    j = i
                    while len(implicit_args) < COMMAND_ARGS[implicit_cmd] and j < len(
                        tokens
                    ):
                        if isinstance(tokens[j], float):
                            implicit_args.append(tokens[j])
                            j += 1
                        else:
                            break

                    if len(implicit_args) == COMMAND_ARGS[implicit_cmd]:
                        implicit_command: list[Union[str, float]] = [
                            implicit_cmd
                        ] + implicit_args
                        commands.append(implicit_command)
                        i = j
                    else:
                        break
        else:
            i += 1

    return commands
