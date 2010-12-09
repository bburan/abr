"""Encapuslate a Default Values Object and Config File"""
 
from inspect import getmembers
import wx
 
class DefaultValueHolder(object):
    """Intended for use with wxConfig (or maybe _winreg) to set up and/or get
       registry key names and values. Name attrs as default*. "default"
       will be stripped of when reading and writing to the config file.
       You may not use the name varDict as one of the variable names."""
 
    def __init__(self, appName, grpName):
        """Open or create the application key"""
        self.appName = appName
        self.grpName = grpName  # if the key or group doesn't exit, it will be created
        self.config = wx.Config(appName)     # Open the file (HKCU in windows registry)
 
    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, "default%s" %name)
        except AttributeError:
            return object.__getattribute__(self, name)
 
    def GetVariables(self):
        return [{"name":var[0][7:], "value":var[1], "type":type(var[1])}
                for var in getmembers(self) if var[0].startswith('default')]
 
    def SetVariables(self, varDict={}, **kwargs):
        kwargs.update(varDict)
        for name, value in kwargs.items():
            setattr(self, "default%s" %name, value)
 
    def InitFromConfig(self):
        config = self.config
        group = self.grpName
 
        if not config.Exists(group):
            self.WriteRegistryGroup(group)
 
        else:
            config.SetPath(group)
            for var in self.GetVariables():
                name = var['name']
                if config.Exists(name):
                    value = self.ReadRegistry(name, var['type'])
                    self.SetVariables({name:value})
                else:
                    self.WriteRegistry(name, var['value'], var['type'])
        config.SetPath("")
 
    def WriteRegistryGroup(self, group):
        self.config.SetPath(group)
        for var in self.GetVariables():
            self.WriteRegistry(var['name'], var['value'], var['type'])
        self.config.SetPath("")
 
    def UpdateConfig(self):
        self.WriteRegistryGroup(self.grpName)
 
    def ReadRegistry(self, name, type):
        value = None
        if type == str:
            value = self.config.Read(name)
        elif type in (int, long):
            value = self.config.ReadInt(name)
        elif type == float:
            value = self.config.ReadFloat(name)
        return value
 
    def WriteRegistry(self, name, value, type):
        if type == str:
            self.config.Write(name, value)
        elif type in (int, long):
            self.config.WriteInt(name, value)
        elif type == float:
            self.config.WriteFloat(name, value)
 
if __name__ == "__main__":
    test = DefaultValueHolder("HETAP Pro 2.00", "Database")
    test.SetVariables(UserName = "peter", Password = "pan", ServerName = "MyServer", database="")
    test.InitFromConfig()
    print test.UserName
    test.defaultvar1=77
    print test.GetVariables()
    #### this also works:
    ## test.defaultUserName = "joe"
