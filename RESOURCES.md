## Building the plugin

Run PyQt5 resource compiler before building
```
pyrcc5 -o resources_rc.py resources.qrc
```

Run the plugin builder tool (pb_tool) to compile and build the plugin
```
pb_tool compile

pb_tool zip
```
