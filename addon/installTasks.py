import os
import shutil
import globalVars


def onRemove():
	configFolder = os.path.join(globalVars.appArgs.configPath, "invisinote")
	if os.path.isdir(configFolder):
		shutil.rmtree(configFolder, ignore_errors=True)
