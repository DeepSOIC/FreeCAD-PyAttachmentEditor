import FreeCAD as App
import Part
from FreeCAD import Units
from Units import MilliMetre as mm
from Units import Degree as deg
from Units import Quantity as Q

if App.GuiUp:
    import FreeCADGui as Gui
    from PySide import QtCore, QtGui
    from FreeCADGui import PySideUic as uic
    
def StrFromLink(feature, subname):
    return feature.Name+ ((":"+subname) if subname else "")
    
def LinkFromStr(strlink, document):
    if len(strlink) == 0:
        return None
    pieces = strlink.split(":")
    
    feature = document.getObject(pieces[0])
    
    subname = ""
    if feature is None:
        raise ValueError("No object named {name}".format(name= pieces[0]))
    if len(pieces) == 2:
        subname = pieces[1]
    elif len(pieces) > 2:
        raise ValueError("Failed to parse link (more than one colon encountered)")
    
    return (feature,subname)

def StrListFromRefs(references):
    '''input: PropertyLinkSubList. Output: list of strings for UI.'''
    return [StrFromLink(feature,subelement) for (feature, subelement) in references]

def RefsFromStrList(strings, document):
    '''input: strings as from UI. Output: list of tuples that can be assigned to PropertyLinkSubList.'''
    refs = []
    for st in strings:
        lnk = LinkFromStr(st, document)
        if lnk is not None:
            refs.append(lnk)
    return refs
        

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
        
        import os
        self.form=uic.loadUi(os.path.dirname(__file__) + os.path.sep + "TaskAttachmentEditor.ui")
        # self.form.setWindowIcon(QtGui.QIcon(":/icons/PartDesign_InternalExternalGear.svg"))
        
        self.refLines = [self.form.lineRef1, 
                         self.form.lineRef2,
                         self.form.lineRef3,
                         self.form.lineRef4]
        self.refButtons = [self.form.buttonRef1,
                           self.form.buttonRef2,
                           self.form.buttonRef3,
                           self.form.buttonRef4]
                           
        for i in range(len(self.refLines)):
            QtCore.QObject.connect(self.refLines[i], QtCore.SIGNAL("textEdited(QString)"), lambda txt: self.lineRefChanged(i,txt))

        for i in range(len(self.refLines)):
            QtCore.QObject.connect(self.refButtons[i], QtCore.SIGNAL("clicked()"), lambda : self.refButtonClicked(i))
        
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
        self.attacher.readParametersFromFeature(self.obj)
        
        plm = self.attacher.SuperPlacement
        try:
            self.form.blockSignals(True)
            self.form.superplacementX.blockSignals(True)
            self.form.superplacementX.setText    (Q(plm.Base.x, mm).UserString)
            self.form.superplacementY.setText    (Q(plm.Base.y, mm).UserString)
            self.form.superplacementZ.setText    (Q(plm.Base.z, mm).UserString)
            self.form.superplacementYaw.setText  (Q(plm.Rotation.toEuler()[0], deg).UserString)
            self.form.superplacementPitch.setText(Q(plm.Rotation.toEuler()[1], deg).UserString)
            self.form.superplacementRoll.setText (Q(plm.Rotation.toEuler()[2], deg).UserString)
            
            strings = StrListFromRefs(self.attacher.References)
            if len(strings) < len(self.refLines):
                strings.extend([""]*(len(self.refLines) - len(strings)))
            for i in range(len(self.refLines)):
                self.refLines[i].setText(strings[i])
        finally:
            self.form.superplacementX.blockSignals(False)
            self.form.superplacementX.blockSignals(False)
            self.form.blockSignals(False)
        
    def superplacementXChanged(self, value):
        print value
        self.attacher.SuperPlacement.Base.x = value
        self.updatePreview()
        
    def lineRefChanged(self, index, value):
        self.updatePreview()
            
    def refButtonClicked(self, index):
        print ("clicked button ",index)
    
    def parseAllRefLines(self):
        self.attacher.References = RefsFromStrList([le.text() for le in self.refLines], self.obj.Document)
        
    def updatePreview(self):
        new_plm = None
        try:
            self.parseAllRefLines()
            
            new_plm = self.attacher.calculateAttachedPlacement(self.obj.Placement)
            if new_plm is None:
                self.form.message.setText("Not attached")
            else:
                self.form.message.setText("Attached")
                self.obj.Placement = new_plm
        except Exception as err:
            self.form.message.setText("Error: {err}".format(err= err.message))

    def accept(self):
        #print 'accept(self)'
        self.writeParameters()
        self.obj.Document.commitTransaction()
        Gui.Control.closeDialog()
                    
    def reject(self):
        #print 'reject(self)'
        self.obj.Document.abortTransaction()
        Gui.Control.closeDialog()


taskd = None

def editAttachment(feature = None):
    global taskd
    if feature is None:
        feature = Gui.Selection.getSelectionEx()[0].Object
    taskd = AttachmentEditorTaskPanel(feature, bool_take_selection= False)
    Gui.Control.showDialog(taskd)
    
# from AttachmentEditor import TaskAttachmentEditor as tae