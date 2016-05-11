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
    KEYmode = QtCore.Qt.ItemDataRole.UserRole # Key to use in Item.data(key) to obtain a mode associated with list item
    KEYon = QtCore.Qt.ItemDataRole.UserRole + 1 # Key to use in Item.data(key) to obtain if the mode is valid
    
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
                           
        self.block = False
                           
        for i in range(len(self.refLines)):
            QtCore.QObject.connect(self.refLines[i], QtCore.SIGNAL("textEdited(QString)"), lambda txt: self.lineRefChanged(i,txt))

        for i in range(len(self.refLines)):
            QtCore.QObject.connect(self.refButtons[i], QtCore.SIGNAL("clicked()"), lambda : self.refButtonClicked(i))
        
        QtCore.QObject.connect(self.form.superplacementX, QtCore.SIGNAL("valueChanged(double)"), self.superplacementXChanged)
        
        self.readParameters()
        self.obj.Document.openTransaction("Edit attachment of {feat}".format(feat= self.obj.Name))
        
        self.updatePreview()
        
    def getStandardButtons(self):
        return int(QtGui.QDialogButtonBox.Ok) | int(QtGui.QDialogButtonBox.Cancel)| int(QtGui.QDialogButtonBox.Apply)
    
    def clicked(self,button):
        if button == QtGui.QDialogButtonBox.Apply:
            print "Apply"
            self.writeParameters()
            updatePreview()
        
    def writeParameters(self):
        "Transfer from the dialog to the object" 
        self.attacher.writeParametersToFeature(self.obj)
        
    
    def readParameters(self):
        "Transfer from the object to the dialog"
        self.attacher.readParametersFromFeature(self.obj)
        
        plm = self.attacher.SuperPlacement
        try:
            old_selfblock = self.block 
            self.block = True
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
            self.block = old_selfblock
        
    def superplacementXChanged(self, value):
        if self.block:
            return
        print value
        self.attacher.SuperPlacement.Base.x = value
        self.updatePreview()
        
    def lineRefChanged(self, index, value):
        if self.block:
            return
        self.updatePreview()
            
    def refButtonClicked(self, index):
        if self.block:
            return
        print ("clicked button ",index)
    
    def parseAllRefLines(self):
        self.attacher.References = RefsFromStrList([le.text() for le in self.refLines], self.obj.Document)
    
    def updateListOfModes(self):
        '''needs suggestor to have been called, and assigned to self.last_sugr'''
        try:
            old_selfblock = self.block 
            self.block = True
            list_widget = self.form.listOfModes
            list_widget.clear()
            sugr = self.last_sugr
            # add valid modes
            for m in sugr["allApplicableModes"]:
                item = QtGui.QListWidgetItem()
                item.setText(m)
                item.setData(self.KEYmode,m)
                item.setData(self.KEYon,True)
                if m == sugr["bestFitMode"]:
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                list_widget.addItem(item)
                item.setSelected(self.attacher.Mode == m)
            # add potential modes
            for m in sugr["reachableModes"].keys():
                item = QtGui.QListWidgetItem()
                txt = m
                listlistrefs = sugr["reachableModes"][m]
                if len(listlistrefs) == 1:
                    txt = "{mode} (add {morerefs})".format(mode= m, morerefs= u"+".join(listlistrefs[0]))
                else:
                    txt = txt + u" (add more references)"
                item.setText(txt)
                item.setData(self.KEYmode,m)
                item.setData(self.KEYon,True)
                if m == sugr["bestFitMode"]:
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                
                #disable this item
                f = item.flags()
                f = f & ~(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable)
                item.setFlags(f)
                
                list_widget.addItem(item)
            
            # re-scan the list to fill in tooltips
            for item in list_widget.findItems("", QtCore.Qt.MatchContains):
                m = item.data(self.KEYmode)
                on = item.data(self.KEYon)
                tip = [u", ".join(refstr) for refstr in self.attacher.getModeInfo(m)["ReferenceCombinations"]]
                #todo: mode purpose tip
                tip = u"Reference combinations:" + u"\n".join(tip) 
                item.setToolTip(tip)

        finally:
            self.block = old_selfblock
        
    def getCurrentMode(self):
        list_widget = self.form.listOfModes
        sel = list_widget.selectedItems()
        if len(sel) == 1:
            if sel[0].data(self.KEYon):
                return str(sel[0].data(self.KEYmode)) # data() returns unicode, which confuses attacher
        # nothing selected in list. Return suggested
        if self.last_sugr is not None:
            if self.last_sugr["message"] == "OK":
                return self.last_sugr["bestFitMode"]
        # no suggested mode. Return current, so it doesn't change
        return self.attacher.Mode
    
    def updatePreview(self):
        new_plm = None
        
        # todo: wrap in error handler when finished debugging
        self.parseAllRefLines()
        self.last_sugr = self.attacher.suggestMapModes()
        if self.last_sugr["message"] == "LinkBroken":
            raise ValueError("Failed to resolve links. {err}".format(err= self.last_sugr["error"]))
            
        self.updateListOfModes()
        
        print repr(self.getCurrentMode())
        self.attacher.Mode = self.getCurrentMode()
            
        try:
            new_plm = self.attacher.calculateAttachedPlacement(self.obj.Placement)
            if new_plm is None:
                self.form.message.setText("Not attached")
            else:
                self.form.message.setText("Attached")
                self.obj.Placement = new_plm
        except Exception as err:
            self.form.message.setText("Error: {err}".format(err= err.message))
        
        if new_plm is not None:
            self.form.groupBox_superplacement.setTitle("Extra placement:")
        else:
            self.form.groupBox_superplacement.setTitle("Extra placement (inactive - not attached):")

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