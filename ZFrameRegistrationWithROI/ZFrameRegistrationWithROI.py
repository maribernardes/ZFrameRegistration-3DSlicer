import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import SimpleITK as sitk
import sitkUtils
#
# ZFrameRegistrationWithROI
#

class OpenSourceZFrameRegistration(object):

  def __init__(self, mrmlScene, volume = None):
    self.inputVolume = volume
    self.mrmlScene = mrmlScene
    self.outputTransform = None
    self._setTransform()

  def setInputVolume(self, volume):
    self.inputVolume = volume
    self._setTransform()

  def _setTransform(self):
    if self.inputVolume:
      seriesNumber = self.inputVolume.GetName().split(":")[0]
      name = seriesNumber + "-ZFrameTransform"
      if self.outputTransform:
        self.mrmlScene.RemoveNode(self.outputTransform)
        self.outputTransform = None
      self.outputTransform = slicer.vtkMRMLLinearTransformNode()
      self.outputTransform.SetName(name)
      self.mrmlScene.AddNode(self.outputTransform)

  def runRegistration(self, start, end):
    if self.inputVolume:
      assert start != -1 and end != -1

      params = {'inputVolume': self.inputVolume, 'startSlice': start, 'endSlice': end,
                'outputTransform': self.outputTransform}
      slicer.cli.run(slicer.modules.zframeregistration, None, params, wait_for_completion=True)

class ZFrameRegistrationWithROI(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "ZFrameRegistrationWithROI" # TODO make this more human readable by adding spaces
    self.parent.categories = ["IGT"]
    self.parent.dependencies = []
    self.parent.contributors = ["Junichi Tokuda (SPL), Simon Di Maio (SPL), Longquan Chen (SPL), Christian Herz (SPL), Andrey Fedorov (SPL)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
It performs a simple thresholding on the input volume and optionally captures a screenshot.
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

#
# ZFrameRegistrationWithROIWidget
#

class ZFrameRegistrationWithROIWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def __init__(self, parent=None):
    ScriptedLoadableModuleWidget.__init__(self, parent)

  def onReload(self):
    ScriptedLoadableModuleWidget.onReload(self)

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    self.setupSliceWidget()
    self.tag = None
    self.registrationGroupBox = qt.QGroupBox()
    self.registrationGroupBoxLayout = qt.QFormLayout()
    self.registrationGroupBox.setLayout(self.registrationGroupBoxLayout)
    self.zFrameTemplateVolumeSelector = slicer.qMRMLNodeComboBox()
    self.zFrameTemplateVolumeSelector.nodeTypes=["vtkMRMLScalarVolumeNode", ""]
    self.zFrameTemplateVolumeSelector.addEnabled = False
    self.zFrameTemplateVolumeSelector.removeEnabled = False
    self.zFrameTemplateVolumeSelector.noneEnabled = True
    self.zFrameTemplateVolumeSelector.showHidden = False
    self.zFrameTemplateVolumeSelector.showChildNodeTypes=False
    self.zFrameTemplateVolumeSelector.selectNodeUponCreation=True
    self.zFrameTemplateVolumeSelector.toolTip="Pick algorithm input."
    self.zFrameTemplateVolumeSelector.setMRMLScene(slicer.mrmlScene)
    self.registrationGroupBoxLayout.addRow("ZFrame template volume: ", self.zFrameTemplateVolumeSelector)
    self.layout.addWidget(self.registrationGroupBox)
    self.layout.addStretch()
    self.annotationLogic = slicer.modules.annotations.logic()
    self.zFrameRegistrationClass = OpenSourceZFrameRegistration

    self.roiObserverTag = None
    self.coverTemplateROI = None
    self.zFrameCroppedVolume = None
    self.zFrameLabelVolume = None
    self.zFrameMaskedVolume = None
    self.otsuOutputVolume = None
    
    self.logic = ZFrameRegistrationWithROILogic()
    self.logic.templateVolume = None
    self.setupManualIndexesGroupBox()
    self.setupActionButtons()
    self.setupConnections()
    self.layout.addWidget(self.zFrameRegistrationManualIndexesGroupBox)
    widget = qt.QWidget()
    rowLayout = qt.QHBoxLayout()
    widget.setLayout(rowLayout)
    rowLayout.addWidget(self.runZFrameRegistrationButton)
    rowLayout.addWidget(self.retryZFrameRegistrationButton)
    self.layout.addWidget(widget)
    self.layout.addStretch(1)
    self.onActivation()

  @staticmethod
  def createCroppedVolume(inputVolume, roi):
    cropVolumeLogic = slicer.modules.cropvolume.logic()
    cropVolumeParameterNode = slicer.vtkMRMLCropVolumeParametersNode()
    cropVolumeParameterNode.SetROINodeID(roi.GetID())
    cropVolumeParameterNode.SetInputVolumeNodeID(inputVolume.GetID())
    cropVolumeParameterNode.SetVoxelBased(True)
    cropVolumeLogic.Apply(cropVolumeParameterNode)
    croppedVolume = slicer.mrmlScene.GetNodeByID(cropVolumeParameterNode.GetOutputVolumeNodeID())
    return croppedVolume

  @staticmethod
  def createMaskedVolume(inputVolume, labelVolume, outputVolumeName=None):
    maskedVolume = slicer.vtkMRMLScalarVolumeNode()
    if outputVolumeName:
      maskedVolume.SetName(outputVolumeName)
    slicer.mrmlScene.AddNode(maskedVolume)
    params = {'InputVolume': inputVolume, 'MaskVolume': labelVolume, 'OutputVolume': maskedVolume}
    slicer.cli.run(slicer.modules.maskscalarvolume, None, params, wait_for_completion=True)
    return maskedVolume

  @staticmethod
  def createLabelMapFromCroppedVolume(volume, name, lowerThreshold=0, upperThreshold=2000, labelValue=1):
    volumesLogic = slicer.modules.volumes.logic()
    labelVolume = volumesLogic.CreateAndAddLabelVolume(volume, name)
    imageData = labelVolume.GetImageData()
    imageThreshold = vtk.vtkImageThreshold()
    imageThreshold.SetInputData(imageData)
    imageThreshold.ThresholdBetween(lowerThreshold, upperThreshold)
    imageThreshold.SetInValue(labelValue)
    imageThreshold.Update()
    labelVolume.SetAndObserveImageData(imageThreshold.GetOutput())
    return labelVolume

  def setupSliceWidget(self):
    self.redWidget = slicer.app.layoutManager().sliceWidget("Red")
    self.redCompositeNode = self.redWidget.mrmlSliceCompositeNode()
    self.redSliceLogic = self.redWidget.sliceLogic()
    self.redSliceNode = self.redSliceLogic.GetSliceNode()

    self.yellowWidget = slicer.app.layoutManager().sliceWidget("Yellow")
    self.yellowCompositeNode = self.yellowWidget.mrmlSliceCompositeNode()
    self.yellowSliceLogic = self.yellowWidget.sliceLogic()
    self.yellowSliceNode = self.yellowSliceLogic.GetSliceNode()

    self.greenWidget = slicer.app.layoutManager().sliceWidget("Green")
    self.greenCompositeNode = self.greenWidget.mrmlSliceCompositeNode()
    self.greenSliceLogic = self.greenWidget.sliceLogic()
    self.greenSliceNode = self.greenSliceLogic.GetSliceNode()

  def setupManualIndexesGroupBox(self):
    self.zFrameRegistrationManualIndexesGroupBox = qt.QGroupBox("Use manual start/end indexes")
    self.zFrameRegistrationManualIndexesGroupBox.setCheckable(True)
    self.zFrameRegistrationManualIndexesGroupBoxLayout = qt.QGridLayout()
    self.zFrameRegistrationManualIndexesGroupBox.setLayout(self.zFrameRegistrationManualIndexesGroupBoxLayout)
    self.zFrameRegistrationManualIndexesGroupBox.checked = False
    self.zFrameRegistrationStartIndex = qt.QSpinBox()
    self.zFrameRegistrationEndIndex = qt.QSpinBox()
    hBox = qt.QWidget()
    rowLayout = qt.QHBoxLayout()
    hBox.setLayout(rowLayout)
    rowLayout.addWidget(qt.QLabel("start"))
    rowLayout.addWidget(self.zFrameRegistrationStartIndex)
    rowLayout.addWidget(qt.QLabel("end"))
    rowLayout.addWidget(self.zFrameRegistrationEndIndex)
    self.zFrameRegistrationManualIndexesGroupBoxLayout.addWidget(hBox, 1, 1, qt.Qt.AlignRight)
  
  def setupActionButtons(self):
    iconSize = qt.QSize(36, 36)
    currentFilePath = os.path.dirname(os.path.realpath(__file__))
    applyFileName = os.path.join(currentFilePath, "Resources", "Icons", "apply.png")
    applyIcon = qt.QIcon(qt.QPixmap(applyFileName))
    retryFileName = os.path.join(currentFilePath, "Resources", "Icons", "retry.png")
    retryIcon = qt.QIcon(qt.QPixmap(retryFileName))
    self.runZFrameRegistrationButton = qt.QPushButton("")
    self.runZFrameRegistrationButton.icon = applyIcon
    self.runZFrameRegistrationButton.iconSize=iconSize
    self.runZFrameRegistrationButton.enabled = True
    self.runZFrameRegistrationButton.toolTip = "Run ZFrame Registration"
    self.retryZFrameRegistrationButton = qt.QPushButton("")
    self.retryZFrameRegistrationButton.icon = retryIcon
    self.retryZFrameRegistrationButton.iconSize = iconSize
    self.retryZFrameRegistrationButton.enabled = True
    self.retryZFrameRegistrationButton.toolTip = "Reset"

  def setupConnections(self):
    self.zFrameTemplateVolumeSelector.connect('currentNodeChanged(bool)', self.loadVolumeAndEnableEditor)
    self.retryZFrameRegistrationButton.clicked.connect(self.onRetryZFrameRegistrationButtonClicked)
    self.runZFrameRegistrationButton.clicked.connect(self.onApplyZFrameRegistrationButtonClicked)  

  def loadVolumeAndEnableEditor(self):
    zFrameTemplateVolume = self.zFrameTemplateVolumeSelector.currentNode()
    if zFrameTemplateVolume:
      self.redCompositeNode.SetBackgroundVolumeID(zFrameTemplateVolume.GetID())
      self.logic.templateVolume = zFrameTemplateVolume
      self.onActivation()
    else:
      self.logic.templateVolume = None

  def onActivation(self):
    self.zFrameRegistrationManualIndexesGroupBox.checked = False
    if self.logic.templateVolume:
      self.initiateZFrameRegistration()
      
  def clearVolumeNodes(self):
    if self.zFrameCroppedVolume:
      slicer.mrmlScene.RemoveNode(self.zFrameCroppedVolume)
      self.zFrameCroppedVolume = None
    if self.zFrameLabelVolume:
      slicer.mrmlScene.RemoveNode(self.zFrameLabelVolume)
      self.zFrameLabelVolume = None
    if self.zFrameMaskedVolume:
      slicer.mrmlScene.RemoveNode(self.zFrameMaskedVolume)
      self.zFrameMaskedVolume = None
    if self.otsuOutputVolume:
      slicer.mrmlScene.RemoveNode(self.otsuOutputVolume)
      self.otsuOutputVolume = None
      
  def initiateZFrameRegistration(self):
    self.clearVolumeNodes()
    if self.coverTemplateROI:
      slicer.mrmlScene.RemoveNode(self.coverTemplateROI)
      self.coverTemplateROI = None
    self.runZFrameRegistrationButton.enabled = False
    self.retryZFrameRegistrationButton.enabled = False
    self.retryZFrameRegistrationButton.enabled = True
    self.logic.zFrameModelNode.GetDisplayNode().SetSliceIntersectionVisibility(False)
    self.logic.zFrameModelNode.SetDisplayVisibility(False)
    slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    self.setBackgroundAndForegroundIDs(foregroundVolumeID=None, backgroundVolumeID=self.logic.templateVolume.GetID())
    self.redSliceNode.SetSliceVisible(True)
    if self.zFrameRegistrationClass is OpenSourceZFrameRegistration:
      self.addROIObserver()
      self.activateCreateROIMode()

  def setBackgroundAndForegroundIDs(self, foregroundVolumeID, backgroundVolumeID):
    self.redCompositeNode.SetForegroundVolumeID(foregroundVolumeID)
    self.redCompositeNode.SetBackgroundVolumeID(backgroundVolumeID)
    self.redSliceNode.SetOrientationToAxial()
    self.yellowCompositeNode.SetForegroundVolumeID(foregroundVolumeID)
    self.yellowCompositeNode.SetBackgroundVolumeID(backgroundVolumeID)
    self.yellowSliceNode.SetOrientationToSagittal()
    self.greenCompositeNode.SetForegroundVolumeID(foregroundVolumeID)
    self.greenCompositeNode.SetBackgroundVolumeID(backgroundVolumeID)
    self.greenSliceNode.SetOrientationToCoronal()

  def addROIObserver(self):
    @vtk.calldata_type(vtk.VTK_OBJECT)
    def onNodeAdded(caller, event, calldata):
      node = calldata
      if isinstance(node, slicer.vtkMRMLAnnotationROINode):
        self.removeROIObserver()
        self.coverTemplateROI = node
        self.runZFrameRegistrationButton.enabled = self.isRegistrationPossible()

    if self.roiObserverTag:
      self.removeROIObserver()
    self.roiObserverTag = slicer.mrmlScene.AddObserver(slicer.vtkMRMLScene.NodeAddedEvent, onNodeAdded)

  def isRegistrationPossible(self):
    return self.coverTemplateROI is not None

  def removeROIObserver(self):
    if self.roiObserverTag:
      self.roiObserverTag = slicer.mrmlScene.RemoveObserver(self.roiObserverTag)

  def activateCreateROIMode(self):
    mrmlScene = self.annotationLogic.GetMRMLScene()
    selectionNode = mrmlScene.GetNthNodeByClass(0, "vtkMRMLSelectionNode")
    selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLAnnotationROINode")
    # self.annotationLogic.StopPlaceMode(False) # BUG: http://na-mic.org/Mantis/view.php?id=4355
    self.annotationLogic.StartPlaceMode(False)

  def onApplyZFrameRegistrationButtonClicked(self):
    zFrameTemplateVolume = self.logic.templateVolume
    try:
      if self.zFrameRegistrationClass is OpenSourceZFrameRegistration:
        self.clearVolumeNodes()
        self.annotationLogic.SetAnnotationLockedUnlocked(self.coverTemplateROI.GetID())
        self.zFrameCroppedVolume = self.createCroppedVolume(zFrameTemplateVolume, self.coverTemplateROI)
        self.zFrameLabelVolume = self.createLabelMapFromCroppedVolume(self.zFrameCroppedVolume, "labelmap")
        self.zFrameMaskedVolume = self.createMaskedVolume(zFrameTemplateVolume, self.zFrameLabelVolume,
                                                                outputVolumeName="maskedTemplateVolume")
        self.zFrameMaskedVolume.SetName(zFrameTemplateVolume.GetName() + "-label")

        if not self.zFrameRegistrationManualIndexesGroupBox.checked:
          start, center, end = self.logic.getROIMinCenterMaxSliceNumbers(self.coverTemplateROI)
          self.otsuOutputVolume = self.logic.applyITKOtsuFilter(self.zFrameMaskedVolume)
          self.logic.dilateMask(self.otsuOutputVolume)
          start, end = self.logic.getStartEndWithConnectedComponents(self.otsuOutputVolume, center)
          self.zFrameRegistrationStartIndex.value = start
          self.zFrameRegistrationEndIndex.value = end
        else:
          start = self.zFrameRegistrationStartIndex.value
          end = self.zFrameRegistrationEndIndex.value
        self.logic.runZFrameOpenSourceRegistration(self.zFrameMaskedVolume,
                                         startSlice=start, endSlice=end)
      else:
        self.logic.runZFrameOpenSourceRegistration(zFrameTemplateVolume)
      self.setBackgroundAndForegroundIDs(foregroundVolumeID=None, backgroundVolumeID=self.logic.templateVolume.GetID())
      self.logic.zFrameModelNode.SetAndObserveTransformNodeID(self.logic.openSourceRegistration.outputTransform.GetID())
      self.logic.zFrameModelNode.GetDisplayNode().SetSliceIntersectionVisibility(True)
      self.logic.zFrameModelNode.SetDisplayVisibility(True)
    except AttributeError as exc:
      slicer.util.errorDisplay("An error occurred. For further information click 'Show Details...'",
                   windowTitle=self.__class__.__name__, detailedText=str(exc.message))
    
  def onRetryZFrameRegistrationButtonClicked(self):
    self.initiateZFrameRegistration()
#
# ZFrameRegistrationWithROILogic
#

class ZFrameRegistrationWithROILogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  ZFRAME_MODEL_PATH = 'zframe-model.vtk'
  ZFRAME_MODEL_NAME = 'ZFrameModel'

  def __init__(self):
    ScriptedLoadableModuleLogic.__init__(self)
    self.redSliceWidget = slicer.app.layoutManager().sliceWidget("Red")
    self.redSliceView = self.redSliceWidget.sliceView()
    self.redSliceLogic = self.redSliceWidget.sliceLogic()
    self.resetAndInitializeData()
    self.otsuFilter = sitk.OtsuThresholdImageFilter()
    self.openSourceRegistration = OpenSourceZFrameRegistration(slicer.mrmlScene)

  def resetAndInitializeData(self):
    self.zFrameModelNode = None
    self.clearOldNodes()
    self.loadZFrameModel()
    
  def cleanup(self):
    super(ZFrameRegistrationWithROILogic, self).cleanup()

  def clearOldNodes(self):
    self.clearOldNodesByName(self.ZFRAME_MODEL_NAME)
    # self.clearOldNodesByName(self.COMPUTED_NEEDLE_MODEL_NAME)

  def loadZFrameModel(self):
    if self.zFrameModelNode:
      slicer.mrmlScene.RemoveNode(node)
      self.zFrameModelNode = None
    currentFilePath = os.path.dirname(os.path.realpath(__file__))
    zFrameModelPath = os.path.join(currentFilePath, "Resources", "zframe", self.ZFRAME_MODEL_PATH)
    _, self.zFrameModelNode = slicer.util.loadModel(zFrameModelPath, returnNode=True)
    slicer.mrmlScene.AddNode(self.zFrameModelNode)
    self.zFrameModelNode.SetName(self.ZFRAME_MODEL_NAME)
    modelDisplayNode = self.zFrameModelNode.GetDisplayNode()
    modelDisplayNode.SetColor(1, 1, 0)
    self.zFrameModelNode.SetDisplayVisibility(False)

  def clearOldNodesByName(self, name):
    collection = slicer.mrmlScene.GetNodesByName(name)
    for index in range(collection.GetNumberOfItems()):
      slicer.mrmlScene.RemoveNode(collection.GetItemAsObject(index))

  def runZFrameOpenSourceRegistration(self, inputVolume, **kwargs):
    self.openSourceRegistration.setInputVolume(inputVolume)

    self.openSourceRegistration.runRegistration(start=kwargs.pop("startSlice"), end=kwargs.pop("endSlice"))
    return True

  @staticmethod
  def getIJKForXYZ(sliceWidget, p):
    xyz = sliceWidget.sliceView().convertRASToXYZ(p)
    layerLogic = sliceWidget.sliceLogic().GetBackgroundLayer()
    xyToIJK = layerLogic.GetXYToIJKTransform()
    ijkFloat = xyToIJK.TransformDoublePoint(xyz)
    ijk = [int(round(value)) for value in ijkFloat]
    return ijk

  @staticmethod
  def getIslandCount(image, index):
    imageSize = image.GetSize()
    index = [0, 0, index]
    extractor = sitk.ExtractImageFilter()
    extractor.SetSize([imageSize[0], imageSize[1], 0])
    extractor.SetIndex(index)
    slice = extractor.Execute(image)
    cc = sitk.ConnectedComponentImageFilter()
    cc.Execute(slice)
    return cc.GetObjectCount()

  @staticmethod
  def dilateMask(label, dilateValue=1.0, erodeValue=0.0, marginSize=5.0):
    imagedata = label.GetImageData()
    dilateErode = vtk.vtkImageDilateErode3D()
    dilateErode.SetInputData(imagedata)
    dilateErode.SetDilateValue(dilateValue)
    dilateErode.SetErodeValue(erodeValue)
    spacing = label.GetSpacing()
    kernelSizePixel = [int(round((abs(marginSize) / spacing[componentIndex] + 1) / 2) * 2 - 1) for componentIndex in
                       range(3)]
    dilateErode.SetKernelSize(kernelSizePixel[0], kernelSizePixel[1], kernelSizePixel[2])
    dilateErode.Update()
    label.SetAndObserveImageData(dilateErode.GetOutput())

  def getROIMinCenterMaxSliceNumbers(self, coverTemplateROI):
    center = [0.0, 0.0, 0.0]
    coverTemplateROI.GetXYZ(center)
    bounds = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    coverTemplateROI.GetRASBounds(bounds)
    pMin = [bounds[0], bounds[2], bounds[4]]
    pMax = [bounds[1], bounds[3], bounds[5]]
    return [self.getIJKForXYZ(self.redSliceWidget, pMin)[2], self.getIJKForXYZ(self.redSliceWidget, center)[2],
            self.getIJKForXYZ(self.redSliceWidget, pMax)[2]]

  def getStartEndWithConnectedComponents(self, volume, center):
    address = sitkUtils.GetSlicerITKReadWriteAddress(volume.GetName())
    image = sitk.ReadImage(address)
    start = self.getStartSliceUsingConnectedComponents(center, image)
    end = self.getEndSliceUsingConnectedComponents(center, image)
    return start, end

  def getStartSliceUsingConnectedComponents(self, center, image):
    sliceIndex = start = center
    while sliceIndex > 0:
      if self.getIslandCount(image, sliceIndex) > 6:
        start = sliceIndex
        sliceIndex -= 1
        continue
      break
    return start

  def getEndSliceUsingConnectedComponents(self, center, image):
    imageSize = image.GetSize()
    sliceIndex = end = center
    while sliceIndex < imageSize[2]:
      if self.getIslandCount(image, sliceIndex) > 6:
        end = sliceIndex
        sliceIndex += 1
        continue
      break
    return end

  def applyITKOtsuFilter(self, volume):
    inputVolume = sitk.Cast(sitkUtils.PullVolumeFromSlicer(volume.GetID()), sitk.sitkInt16)
    self.otsuFilter.SetInsideValue(0)
    self.otsuFilter.SetOutsideValue(1)
    otsuITKVolume = self.otsuFilter.Execute(inputVolume)
    return sitkUtils.PushToSlicer(otsuITKVolume, "otsuITKVolume", 0, True)

class ZFrameRegistrationWithROITest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_ZFrameRegistrationWithROI1()

  def test_ZFrameRegistrationWithROI1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import urllib
    downloads = (
        ('http://slicer.kitware.com/midas3/download?items=5767', 'FA.nrrd', slicer.util.loadVolume),
        )

    for url,name,loader in downloads:
      filePath = slicer.app.temporaryPath + '/' + name
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        logging.info('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
      if loader:
        logging.info('Loading %s...' % (name,))
        loader(filePath)
    self.delayDisplay('Finished with download and loading')

    #volumeNode = slicer.util.getNode(pattern="FA")
    #logic = ZFrameRegistrationWithROILogic()
    #self.assertIsNotNone( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')
