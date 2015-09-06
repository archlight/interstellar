import os
import re
import json

reglib = [
('T1','(Bump \(\d+\)).*?(FXBasketAutocal_caller.*?Matrix not positive definite).*?(Try bumping.*?in)'),
('T2','(Bump \(\d+\)).*?(GentooBehaviour).*?(Cross Correlation Calibration).*?(FX3D_CrossFxCorrel_Calibration)'),
('T3','(Bump \(\d+\)).*?(GentooBehaviour).*?(Correl calibration\s(\w+)\s.*?Try bumping up (\w+) volatility)'),
('T4','(Bump \(\d+\)).*?MultiFXPowerDualBehaviour.*?Correl calibration\s(\w+)\s.*?Try bumping up (\w+) volatility'),
('T5', '(Bump \(\d+\)).*(MultiFXPowerDualBehaviour).*?(FX3D Correl Calibration failed, time = \d+\.\d+)'),
('T6', '(Restart mechanism unexpectedly triggered)'),
('T7', '(Invalid Parameter trapped in CRT)'),
('T8', 'Failed in (.*?:)')
]

def simplify(jsonData):
    d = []
    for row in json.loads(jsonData):
        for errorType, pattern in reglib:
            m = re.search(pattern, row["MESSAGE_TEXT"].replace('\n', ''))
            if m:
                row["TYPE"] = errorType
                row["TAGS"] = list(m.groups())
                break
        if not "TYPE" in row:
            row["TYPE"] = "T0"
            row["TAGS"] = ["other"]
        d.append(row)
    return d
