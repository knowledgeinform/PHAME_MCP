# pip install pywin32
# python -m pywin32_postinstall -install

import win32com.client

# swApp = win32com.client.Dispatch("SldWorks.SldWorks")

# New Solidworks instance (allegedly)
# swApp = win32com.client.DispatchEx("SldWorks.Application")

# Attach ot exisiting solidworks instance
swApp = win32com.client.Dispatch("SldWorks.Application")

# Late-binding can be flaky with SolidWorks’ type library. This usually improves reliability:
# TODO need to run some makepy routine
# swApp = win32com.client.gencache.EnsureDispatch("SldWorks.Application")

swApp.Visible = True
print("SolidWorks version:", swApp.RevisionNumber)