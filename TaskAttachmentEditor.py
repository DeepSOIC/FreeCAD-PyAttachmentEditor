import FreeCAD as App
import Part

if App.GuiUp:
    import FreeCADGui as Gui
    from PySide import QtCore, QtGui
    from FreeCADGui import PySideUic as uic

class AttachmentEditorTaskPanel:
    '''The editmode TaskPanel for attachment editing'''
    def __init__(self, obj_to_attach, bool_take_selection):
        self.obj = obj_to_attach
        if hasattr(obj_to_attach,"Attacher"):
            self.attacher = obj_to_attach.Attacher
        elif hasattr(obj_to_attach,"AttacherType"):
            self.attacher = Part.AttachEngine(obj_to_attach.AttacherType)
        else:
            raise TypeError("Object {objname} is not attachable. It has no Attacher attribute, and no AttacherType attribute"
                             .format(objname= obj_to_attach.Label))
        self.attacher.readParametersFromFeature(obj_to_attach)
        
        import os
        self.form=uic.loadUi(os.path.dirname(__file__) + os.path.sep + "TaskAttachmentEditor.ui")
        # self.form.setWindowIcon(QtGui.QIcon(":/icons/PartDesign_InternalExternalGear.svg"))
        
        QtCore.QObject.connect(self.form.superplacementX, QtCore.SIGNAL("valueChanged(double)"), self.superplacementXChanged)
        
        self.readParameters()
        self.obj.Document.openTransaction("Edit attachment of {feat}".format(feat= self.obj.Name))
        
    def getStandardButtons(self):
        return int(QtGui.QDialogButtonBox.Ok) | int(QtGui.QDialogButtonBox.Cancel)| int(QtGui.QDialogButtonBox.Apply)
    
    def clicked(self,button):
        if button == QtGui.QDialogButtonBox.Apply:
            print "Apply"
            self.writeParameters()
            updatePreview()
        
    def writeParameters(self):
        "Transfer from the dialog to the object" 
        #self.obj.PressureAngle  = self.form.Quantity_PressureAngle.text()
        self.attacher.writeParametersToFeature(self.obj)
        
    
    def readParameters(self):
        "Transfer from the object to the dialog"
        self.form.superplacementX.setValue(self.attacher.SuperPlacement.Base.x)
        
    def superplacementXChanged(self, value):
        print value
        self.attacher.SuperPlacement.Base.x = value
        self.updatePreview()
        
    def updatePreview(self):
        new_plm = None
        try:
            new_plm = self.attacher.calculateAttachedPlacement(self.obj.Placement)
        except Exception as err:
            self.form.message.setText("Error: {err}".format(err= err.message))
        if new_plm is None:
            self.form.message.setText("Not attached")
        else:
            self.form.message.setText("Attached")
            self.obj.Placement = new_plm

    def accept(self):
        #print 'accept(self)'
        self.writeParameters()
        self.obj.Document.commitTransaction()
        FreeCADGui.Control.closeDialog()
                    
    def reject(self):
        #print 'reject(self)'
        self.obj.Document.abortTransaction()
        FreeCADGui.Control.closeDialog()


taskd = None

def editAttachment(feature = None):
    global taskd
    if feature is None:
        feature = Gui.Selection.getSelectionEx()[0].Object
    taskd = AttachmentEditorTaskPanel(feature, bool_take_selection= False)
    Gui.Control.showDialog(taskd)
    
# from AttachmentEditor import TaskAttachmentEditor as tae