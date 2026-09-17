"""
SVG Path Morph - Core morphing functionality.

This module provides the compile() and morph() functions for
creating weighted combinations of SVG paths.
"""

from dataclasses import dataclass

from .parser import parse


@dataclass
class CompiledPaths:
    """
    A compiled representation of SVG paths ready for morphing.

    Attributes:
        commands: List of SVG command letters (e.g., ['M', 'L', 'C'])
        average: Average parameters for each command across all paths
        diffs: Difference from average for each path's parameters
    """

    commands: list[str]
    average: list[list[float]]
    diffs: list[list[list[float]]]


def compile(paths: list[str]) -> CompiledPaths:
    """
    Takes a list of SVG path strings and returns a compiled object
    that can be used to easily morph between them.

    To be used in combination with `morph()`, e.g.:

        paths = compile(['M0,0 L100,100', 'M5,5 L250,50'])

        # Get the path halfway between the two paths
        between = morph(paths, [0.5, 0.5])

    Args:
        paths: SVG path strings. Each string must be a variation of the
            same path, i.e. same number of commands in the same order.
            The command parameters may vary as needed.

    Returns:
        A CompiledPaths object containing:
        1. commands: A list of path commands
        2. average: Command parameters averaged between all passed paths
        3. diffs: Command parameters relative to the average for each path

    Raises:
        ValueError: If no paths are provided, paths have different numbers
            of commands, or paths have different command sequences.
    """
    n_paths = len(paths)
    if n_paths == 0:
        raise ValueError("compile() must receive at least one path.")

    # Parse all paths
    parsed_paths = [parse(path) for path in paths]

    # Extract commands from the first path as the template
    commands = [cmd[0] for cmd in parsed_paths[0]]

    # Validate that all paths have the same number of commands
    for path in parsed_paths:
        if len(path) != len(commands):
            raise ValueError("All paths must have the same number of commands.")

    # Validate that all paths have the same command sequence
    for i, cmd in enumerate(commands):
        for path in parsed_paths:
            if path[i][0] != cmd:
                raise ValueError(
                    "All paths must be variations of the same sequence of commands."
                )

    # Initialize average and diffs arrays
    average: list[list[float]] = []
    diffs: list[list[list[float]]] = []

    # Build an average path
    for c in range(len(commands)):
        n_values = len(parsed_paths[0][c]) - 1  # Exclude the command letter

        avg_cmd: list[float] = []
        diff_cmd: list[list[float]] = []

        for v in range(n_values):
            # Calculate the average for this parameter
            total = 0.0
            for p in range(n_paths):
                param = parsed_paths[p][c][v + 1]
                total += param
            avg_value = total / n_paths
            avg_cmd.append(avg_value)

            # Calculate differences from the average for each path
            param_diffs: list[float] = []
            for p in range(n_paths):
                param = parsed_paths[p][c][v + 1]
                param_diffs.append(param - avg_value)
            diff_cmd.append(param_diffs)

        average.append(avg_cmd)
        diffs.append(diff_cmd)

    return CompiledPaths(commands=commands, average=average, diffs=diffs)


def morph(compiled: CompiledPaths, weights: list[float]) -> str:
    """
    Takes a compiled paths object and a list of weights and returns
    a morphed path as a weighted combination of the paths.

    Example:
        # Provided two variations of the same path
        angry_face = 'M0,0 L100,100...'
        happy_face = 'M0,0 L100,100...'

        paths = compile([angry_face, happy_face])

        # Get the path halfway between the two paths, i.e. 50% angry, 50% happy
        neutral_face = morph(paths, [0.5, 0.5])

    Args:
        compiled: The compiled paths object (see compile())
        weights: A list of weights, one for each path in the compiled object.

    Returns:
        The weighted combination of the compiled paths as an SVG path string.

    Raises:
        ValueError: If the number of weights doesn't match the number of paths.
    """
    # Get the number of paths from the diffs structure
    n_paths = len(compiled.diffs[0][0])

    if len(weights) != n_paths:
        raise ValueError("Weights must have the same length as the number of paths.")

    # Create a copy of the average to morph
    morphed = [cmd[:] for cmd in compiled.average]

    # Build the morphed path string
    morphed_path = ""
    for c, cmd in enumerate(compiled.commands):
        morphed_path += cmd
        for v in range(len(compiled.average[c])):
            # Calculate weighted sum of differences
            weighted_sum = sum(
                compiled.diffs[c][v][p] * weights[p] for p in range(n_paths)
            )
            morphed[c][v] += weighted_sum
            morphed_path += str(morphed[c][v]) + " "

    return morphed_path.rstrip()
