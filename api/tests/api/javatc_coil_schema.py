"""
The JavaTC example coil expressed as an API request payload (plain dicts,
exactly as a frontend would send). Kept parallel to
tests/simulation/test_coils.JAVATC_EXAMPLE_COIL.
"""

_DISC = 0.03125

JAVATC_COIL_PAYLOAD = {
    "secondary": {
        "material": "copper",
        "turn_fxn": {"kind": "uniform", "total_turns": 895},
        "start": [2.26925, 23.0],
        "end": [2.26925, 44.8085],
        "wire_dia": 0.020101,
    },
    "primary": {
        "material": "copper",
        "turn_fxn": {"kind": "uniform", "total_turns": 8.438},
        "cross_section": {"kind": "circular", "diameter": 0.25},
        "start": [3.75, 23.0],
        "end": [7.969, 23.0],
        "tank_capacitance": 0.0188e-6,
        "lead_length": 30.0,
        "lead_dia": 0.2,
    },
    "toploads": [
        {
            "material": "aluminum",
            "shape": {"kind": "circle", "center": [7.375, 48.8085], "radius": 3.125},
        },
        {
            "material": "aluminum",
            "shape": {
                "kind": "rectangle",
                "vertices": [
                    [-0.05, 48.8085 - _DISC],
                    [8.25, 48.8085 - _DISC],
                    [8.25, 48.8085 + _DISC],
                    [-0.05, 48.8085 + _DISC],
                ],
            },
        },
    ],
    "grounds": [],
    "r_max": 100,
    "z_max": 150,
    "unit_scale": 0.0254,
    "discretization_order": 30,
}
