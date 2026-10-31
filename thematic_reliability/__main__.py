"""Run the drift detection example: python -m thematic_reliability"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from thematic_reliability import (
    Codebook, Code, ThematicNetwork, BasicTheme, OrganizingTheme,
    GlobalTheme, measure_drift, cohen_kappa, drift_impact,
)

codebook = Codebook(
    name="Patient Experience",
    description="Codes for primary care patient experience interviews",
)
codebook.add(Code("ACCESS", "Ease or difficulty of getting an appointment"))
codebook.add(Code("COMMUNICATION", "Quality of information exchange with provider"))
codebook.add(Code("CONTINUITY", "Seeing the same provider over time"))
codebook.add(Code("TRUST", "Confidence in the provider's competence or intent"))
codebook.add(Code("WAIT", "Time spent waiting, in any context"))

print("Codebook: %s (%d codes)" % (codebook.name, len(codebook)))
print("Categories:", codebook.categories())
print()

calibration = {
    "u01": "ACCESS",     "u02": "COMMUNICATION", "u03": "TRUST",
    "u04": "WAIT",       "u05": "CONTINUITY",    "u06": "ACCESS",
    "u07": "COMMUNICATION", "u08": "TRUST",      "u09": "WAIT",
    "u10": "CONTINUITY",
}

recodings = [
    {  # Week 2: still close
        "u01": "ACCESS",     "u02": "COMMUNICATION", "u03": "TRUST",
        "u04": "WAIT",       "u05": "CONTINUITY",    "u06": "ACCESS",
        "u07": "COMMUNICATION", "u08": "TRUST",
        "u09": "ACCESS",     "u10": "CONTINUITY",
    },
    {  # Week 5: ACCESS/WAIT and TRUST/COMMUNICATION blurring
        "u01": "ACCESS",     "u02": "COMMUNICATION",
        "u03": "COMMUNICATION", "u04": "ACCESS",
        "u05": "CONTINUITY", "u06": "ACCESS",
        "u07": "COMMUNICATION", "u08": "TRUST",
        "u09": "ACCESS",     "u10": "TRUST",
    },
    {  # Week 8: substantial drift
        "u01": "COMMUNICATION", "u02": "COMMUNICATION",
        "u03": "COMMUNICATION", "u04": "ACCESS",
        "u05": "CONTINUITY",    "u06": "WAIT",
        "u07": "TRUST",         "u08": "TRUST",
        "u09": "ACCESS",        "u10": "CONTINUITY",
    },
]

report = measure_drift(
    baseline_codings=calibration,
    recodings=recodings,
    categories=codebook.categories(),
)
print(report.summary())
print()

# Inter-rater check
second_coder = {
    "u01": "ACCESS",     "u02": "COMMUNICATION", "u03": "TRUST",
    "u04": "WAIT",       "u05": "CONTINUITY",    "u06": "ACCESS",
    "u07": "TRUST",      "u08": "TRUST",         "u09": "WAIT",
    "u10": "CONTINUITY",
}
units = sorted(calibration)
kappa, p_obs, p_exp = cohen_kappa(
    [calibration[u] for u in units],
    [second_coder[u] for u in units],
    codebook.categories(),
)
print("Inter-rater reliability (calibration set):")
print("  kappa=%.4f  observed=%.1f%%  expected=%.1f%%" % (kappa, p_obs * 100, p_exp * 100))
print()

# Thematic network + drift impact
network = ThematicNetwork(name="Patient Experience Network")
network.add_basic(BasicTheme("Availability", codes=["ACCESS", "WAIT"]))
network.add_basic(BasicTheme("Relationship", codes=["COMMUNICATION", "TRUST"]))
network.add_basic(BasicTheme("Stability", codes=["CONTINUITY"]))
network.add_organizing(OrganizingTheme("System responsiveness", basic_themes=["Availability"]))
network.add_organizing(OrganizingTheme("Therapeutic alliance", basic_themes=["Relationship", "Stability"]))
network.add_global(GlobalTheme("Care quality as experienced", organizing_themes=["System responsiveness", "Therapeutic alliance"]))

print("Thematic network: %s" % network.name)
cov = network.coverage(codebook.categories())
print("  Covered: %s" % cov["covered"])
print("  Uncovered: %s" % cov["uncovered"])
print()

impact = drift_impact(network, report)
if impact:
    print("Drift impact on thematic network:")
    for item in impact:
        print("  %s '%s': affected by drifting code(s) %s"
              % (item["level"], item["name"], ", ".join(item["drifting_codes"])))
else:
    print("No drift impact on thematic network.")
