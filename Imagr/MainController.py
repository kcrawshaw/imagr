# -*- coding: utf-8 -*-
#
#  MainController.py
#  Imagr
#
#  Created by Graham Gilbert on 04/04/2015.
#  Copyright (c) 2015 Graham Gilbert. All rights reserved.
#

import objc
import FoundationPlist
import os
from SystemConfiguration import *
from Foundation import *
from AppKit import *
from Cocoa import *
import subprocess
import sys
import macdisk
import urllib2
import Utils
import PyObjCTools
import tempfile
import shutil
import Quartz

class MainController(NSObject):

    mainWindow = objc.IBOutlet()

    utilities_menu = objc.IBOutlet()

    theTabView = objc.IBOutlet()
    introTab = objc.IBOutlet()
    loginTab = objc.IBOutlet()
    mainTab = objc.IBOutlet()
    errorTab = objc.IBOutlet()

    password = objc.IBOutlet()
    passwordLabel = objc.IBOutlet()
    loginLabel = objc.IBOutlet()
    loginButton = objc.IBOutlet()
    errorField = objc.IBOutlet()

    progressIndicator = objc.IBOutlet()
    progressText = objc.IBOutlet()

    startUpDiskPanel = objc.IBOutlet()
    startUpDiskText = objc.IBOutlet()
    startupDiskCancelButton = objc.IBOutlet()
    startupDiskDropdown = objc.IBOutlet()
    startupDiskRestartButton = objc.IBOutlet()

    chooseTargetPanel = objc.IBOutlet()
    chooseTargetDropDown = objc.IBOutlet()
    chooseTargetCancelButton = objc.IBOutlet()
    chooseTargetPanelSelectTarget = objc.IBOutlet()

    cancelAndRestartButton = objc.IBOutlet()
    reloadWorkflowsButton = objc.IBOutlet()
    reloadWorkflowsMenuItem = objc.IBOutlet()
    chooseWorkflowDropDown = objc.IBOutlet()
    chooseWorkflowLabel = objc.IBOutlet()

    runWorkflowButton = objc.IBOutlet()
    workflowDescriptionView = objc.IBOutlet()
    workflowDescription = objc.IBOutlet()

    imagingProgress = objc.IBOutlet()
    imagingLabel = objc.IBOutlet()
    imagingProgressPanel = objc.IBOutlet()
    imagingProgressDetail = objc.IBOutlet()

    # former globals, now instance variables
    hasLoggedIn = None
    volumes = None
    passwordHash = None
    workflows = None
    targetVolume = None
    workVolume = None
    selectedWorkflow = None
    packages_to_install = None
    restartAction = None
    blessTarget = None
    errorMessage = None
    alert = None

    def errorPanel(self, error):
        errorText = str(error)
        self.alert = NSAlert.alertWithMessageText_defaultButton_alternateButton_otherButton_informativeTextWithFormat_(
            NSLocalizedString(errorText, None),
            NSLocalizedString(u"Okay", None),
            objc.nil,
            objc.nil,
            NSLocalizedString(u"", None))

        self.alert.beginSheetModalForWindow_modalDelegate_didEndSelector_contextInfo_(
            self.mainWindow, self, self.setStartupDisk_, objc.nil)

    def runStartupTasks(self):
        self.mainWindow.center()
        # Run app startup - get the images, password, volumes - anything that takes a while

        self.progressText.setStringValue_("Application Starting...")
        self.progressIndicator.setIndeterminate_(True)
        self.progressIndicator.setUsesThreadedAnimation_(True)
        self.progressIndicator.startAnimation_(self)
        self.buildUtilitiesMenu()
        NSThread.detachNewThreadSelector_toTarget_withObject_(self.loadData, self, None)

    def loadData(self):

        pool = NSAutoreleasePool.alloc().init()
        self.volumes = macdisk.MountedVolumes()

        theURL = Utils.getServerURL()
        if theURL:
            plistData = Utils.downloadFile(theURL)
            if plistData:
                try:
                    converted_plist = FoundationPlist.readPlistFromString(plistData)
                except:
                    self.errorMessage = "Configuration plist couldn't be read."
                try:
                    self.passwordHash = converted_plist['password']
                except:
                    self.errorMessage = "Password wasn't set."

                try:
                    self.workflows = converted_plist['workflows']
                except:
                    self.errorMessage = "No workflows found in the configuration plist."
            else:
                self.errorMessage = "Couldn't get configuration plist from server."
        else:
            self.errorMessage = "Configuration URL wasn't set."

        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            self.loadDataComplete, None, YES)
        del pool

    def loadDataComplete(self):
        self.reloadWorkflowsMenuItem.setEnabled_(True)
        if self.errorMessage:
            self.theTabView.selectTabViewItem_(self.errorTab)
            self.errorPanel(self.errorMessage)
        else:
            if self.hasLoggedIn:
                self.theTabView.selectTabViewItem_(self.mainTab)
                self.chooseImagingTarget_(None)
                self.enableAllButtons_(self)
            else:
                self.theTabView.selectTabViewItem_(self.loginTab)
                self.mainWindow.makeFirstResponder_(self.password)

    @objc.IBAction
    def reloadWorkflows_(self, sender):
        self.reloadWorkflowsMenuItem.setEnabled_(False)
        self.progressText.setStringValue_("Reloading workflows...")
        self.progressIndicator.setIndeterminate_(True)
        self.progressIndicator.setUsesThreadedAnimation_(True)
        self.progressIndicator.startAnimation_(self)
        self.theTabView.selectTabViewItem_(self.introTab)
        NSThread.detachNewThreadSelector_toTarget_withObject_(self.loadData, self, None)

    @objc.IBAction
    def login_(self, sender):
        if self.passwordHash:
            password_value = self.password.stringValue()
            if Utils.getPasswordHash(password_value) != self.passwordHash or password_value == "":
                self.errorField.setEnabled_(sender)
                self.errorField.setStringValue_("Incorrect password")
                self.shakeWindow()

            else:
                self.theTabView.selectTabViewItem_(self.mainTab)
                self.chooseImagingTarget_(None)
                self.enableAllButtons_(self)
                self.hasLoggedIn = True

    @objc.IBAction
    def setStartupDisk_(self, sender):
        if self.alert:
            self.alert.window().orderOut_(self)
            self.alert = None

        # Prefer to use the built in Startup disk pane
        if os.path.exists("/Applications/Utilities/Startup Disk.app"):
            Utils.launchApp("/Applications/Utilities/Startup Disk.app")
        else:
            self.restartAction = 'restart'
            # This stops the console being spammed with: unlockFocus called too many times. Called on <NSButton
            NSGraphicsContext.saveGraphicsState()
            self.disableAllButtons(sender)
            # clear out the default junk in the dropdown
            self.startupDiskDropdown.removeAllItems()
            list = []
            for volume in self.volumes:
                list.append(volume.mountpoint)

            # Let's add the items to the popup
            self.startupDiskDropdown.addItemsWithTitles_(list)
            NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
                self.startUpDiskPanel, self.mainWindow, self, None, None)
            NSGraphicsContext.restoreGraphicsState()


    @objc.IBAction
    def closeStartUpDisk_(self, sender):
        self.enableAllButtons_(sender)
        NSApp.endSheet_(self.startUpDiskPanel)
        self.startUpDiskPanel.orderOut_(self)

    @objc.IBAction
    def openProgress_(self, sender):
        NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
            self.progressPanel, self.mainWindow, self, None, None)

    @objc.IBAction
    def chooseImagingTarget_(self, sender):
        self.disableAllButtons(sender)
        NSGraphicsContext.saveGraphicsState()
        self.chooseTargetDropDown.removeAllItems()
        list = []
        for volume in self.volumes:
            if volume.mountpoint != '/':
                if volume.mountpoint.startswith("/Volumes"):
                    if volume.mountpoint != '/Volumes':
                        if volume.writable:
                            list.append(volume.mountpoint)
         # No writable volumes, this is bad.
        if len(list) == 0:
            alert = NSAlert.alertWithMessageText_defaultButton_alternateButton_otherButton_informativeTextWithFormat_(
                NSLocalizedString(u"No writable volumes found", None),
                NSLocalizedString(u"Restart", None),
                NSLocalizedString(u"Open Disk Utility", None),
                objc.nil,
                NSLocalizedString(u"No writable volumes were found on this Mac.", None))

            alert.beginSheetModalForWindow_modalDelegate_didEndSelector_contextInfo_(
                self.mainWindow, self, self.noVolAlertDidEnd_returnCode_contextInfo_, objc.nil)
        # If there's only one volume, we're going to use that and move on to selecting the workflow
        self.enableAllButtons_(self)
        if len(list) == 1:
            self.targetVolume = list[0]
            self.selectWorkflow_(sender)
            for volume in self.volumes:
                if str(volume.mountpoint) == str(self.targetVolume):
                    imaging_target = volume
                    self.workVolume = volume
                    break
            # We'll move on to the select workflow bit when it exists
        else:
            self.chooseTargetDropDown.addItemsWithTitles_(list)
            NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
                self.chooseTargetPanel, self.mainWindow, self, None, None)
        NSGraphicsContext.restoreGraphicsState()

    @PyObjCTools.AppHelper.endSheetMethod
    def noVolAlertDidEnd_returnCode_contextInfo_(self, alert, returncode, contextinfo):
        if returncode == NSAlertDefaultReturn:
            self.setStartupDisk_(None)
        else:
            Utils.launchApp('/Applications/Utilities/Disk Utility.app')
            # cmd = ['/Applications/Utilities/Disk Utility.app/Contents/MacOS/Disk Utility']
            # proc = subprocess.call(cmd)
            #NSWorkspace.sharedWorkspace().launchApplication_("/Applications/Utilities/Disk Utility.app")
            alert = NSAlert.alertWithMessageText_defaultButton_alternateButton_otherButton_informativeTextWithFormat_(
                NSLocalizedString(u"Rescan for volumes", None),
                NSLocalizedString(u"Rescan", None),
                objc.nil,
                objc.nil,
                NSLocalizedString(u"Rescan for volumes.", None))

            alert.beginSheetModalForWindow_modalDelegate_didEndSelector_contextInfo_(
                self.mainWindow, self, self.rescanAlertDidEnd_returnCode_contextInfo_, objc.nil)

    @PyObjCTools.AppHelper.endSheetMethod
    def rescanAlertDidEnd_returnCode_contextInfo_(self, alert, returncode, contextinfo):
        self.progressText.setStringValue_("Reloading Volumes...")
        self.theTabView.selectTabViewItem_(self.introTab)
        # NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
        #     self.progressPanel, self.mainWindow, self, None, None)
        NSThread.detachNewThreadSelector_toTarget_withObject_(self.loadData, self, None)


    @objc.IBAction
    def selectImagingTarget_(self, sender):
        self.targetVolume = self.chooseTargetDropDown.titleOfSelectedItem()
        for volume in self.volumes:
            if str(volume.mountpoint) == str(self.targetVolume):
                self.workVolume = volume
                break
        self.enableAllButtons_(sender)
        NSApp.endSheet_(self.chooseTargetPanel)
        self.chooseTargetPanel.orderOut_(self)
        self.selectWorkflow_(self)


    @objc.IBAction
    def closeImagingTarget_(self, sender):
        self.enableAllButtons_(sender)
        NSApp.endSheet_(self.chooseTargetPanel)
        self.chooseTargetPanel.orderOut_(self)
        self.setStartupDisk_(sender)

    @objc.IBAction
    def selectWorkflow_(self, sender):
        self.chooseWorkflowDropDown.removeAllItems()
        list = []
        for workflow in self.workflows:
            list.append(workflow['name'])

        self.chooseWorkflowDropDown.addItemsWithTitles_(list)
        self.chooseWorkflowLabel.setHidden_(False)
        self.chooseWorkflowDropDown.setHidden_(False)
        self.workflowDescriptionView.setHidden_(False)
        self.runWorkflowButton.setHidden_(False)
        self.chooseWorkflowDropDownDidChange_(sender)

    @objc.IBAction
    def chooseWorkflowDropDownDidChange_(self, sender):
        selected_workflow = self.chooseWorkflowDropDown.titleOfSelectedItem()
        for workflow in self.workflows:
            if selected_workflow == workflow['name']:
                try:
                    self.workflowDescription.setString_(workflow['description'])
                except:
                    self.workflowDescription.setString_("")
                break

    @objc.IBAction
    def runWorkflow_(self, sender):
        '''Set up the selected workflow to run on secondary thread'''
        self.imagingProgress.setHidden_(False)
        self.imagingLabel.setHidden_(False)
        self.reloadWorkflowsButton.setEnabled_(False)
        self.reloadWorkflowsMenuItem.setEnabled_(False)
        self.cancelAndRestartButton.setEnabled_(False)
        self.chooseWorkflowLabel.setEnabled_(True)
        self.chooseWorkflowDropDown.setEnabled_(False)
        # self.workflowDescriptionView.setEnabled_(True)
        self.runWorkflowButton.setEnabled_(False)
        self.cancelAndRestartButton.setEnabled_(False)
        self.imagingLabel.setStringValue_("Preparing to run workflow...")
        self.imagingProgressDetail.setStringValue_('')
        NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
            self.imagingProgressPanel, self.mainWindow, self, None, None)
        # initialize the progress bar
        self.imagingProgress.setMinValue_(0.0)
        self.imagingProgress.setMaxValue_(100.0)
        self.imagingProgress.setIndeterminate_(True)
        self.imagingProgress.setUsesThreadedAnimation_(True)
        self.imagingProgress.startAnimation_(self)
        NSThread.detachNewThreadSelector_toTarget_withObject_(
            self.processWorkflowOnThread, self, None)

    def updateProgressWithInfo_(self, info):
        '''UI stuff should be done on the main thread. Yet we do all our interesting work
        on a secondary thread. So to update the UI, the secondary thread should call this
        method using performSelectorOnMainThread_withObject_waitUntilDone_'''
        if 'title' in info.keys():
            self.imagingLabel.setStringValue_(info['title'])
        if 'percent' in info.keys():
            if float(info['percent']) < 0:
                if not self.imagingProgress.isIndeterminate():
                    self.imagingProgress.setIndeterminate_(True)
                    self.imagingProgress.startAnimation_(self)
            else:
                if self.imagingProgress.isIndeterminate():
                    self.imagingProgress.stopAnimation_(self)
                    self.imagingProgress.setIndeterminate_(False)
                self.imagingProgress.setDoubleValue_(float(info['percent']))
        if 'detail' in info.keys():
            self.imagingProgressDetail.setStringValue_(info['detail'])

    def updateProgressTitle_Percent_Detail_(self, title, percent, detail):
        '''Wrapper method that calls the UI update method on the main thread'''
        info = {}
        if title is not None:
            info['title'] = title
        if percent is not None:
            info['percent'] = percent
        if detail is not None:
            info['detail'] = detail
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            self.updateProgressWithInfo_, info, objc.NO)

    def processWorkflowOnThread(self, sender):
        '''Process the selected workflow'''
        pool = NSAutoreleasePool.alloc().init()
        selected_workflow = self.chooseWorkflowDropDown.titleOfSelectedItem()
        # let's get the workflow
        self.selectedWorkflow = None
        for workflow in self.workflows:
            if selected_workflow == workflow['name']:
                self.selectedWorkflow = workflow
                break
        if self.selectedWorkflow:
            if 'restart_action' in self.selectedWorkflow:
                self.restartAction = self.selectedWorkflow['restart_action']
            if 'bless_target' in self.selectedWorkflow:
                self.blessTarget = self.selectedWorkflow['bless_target']
            else:
                self.blessTarget = True

            self.restoreImage()
            if not self.errorMessage:
                self.downloadAndInstallPackages()
            if not self.errorMessage:
                self.downloadAndCopyPackages()
            if not self.errorMessage:
                self.copyFirstBootScripts()
            if not self.errorMessage:
                self.runPreFirstBootScript()

        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            self.processWorkflowOnThreadComplete, None, YES)
        del pool

    def processWorkflowOnThreadComplete(self):
        '''Done running workflow, restart to imaged volume'''
        NSApp.endSheet_(self.imagingProgressPanel)
        self.imagingProgressPanel.orderOut_(self)
        if self.errorMessage:
            self.theTabView.selectTabViewItem_(self.errorTab)
            self.errorPanel(self.errorMessage)
        elif self.restartAction == 'restart' or self.restartAction == 'shutdown':
            self.restartToImagedVolume()
        else:
            self.openEndWorkflowPanel()

    def restoreImage(self):
        dmgs_to_restore = [item.get('url') for item in self.selectedWorkflow['components']
                           if item.get('type') == 'image' and item.get('url')]
        if dmgs_to_restore:
            self.Clone(dmgs_to_restore[0], self.targetVolume)

    def Clone(self, source, target, erase=True, verify=True, show_activity=True):
        """A wrapper around 'asr' to clone one disk object onto another.

        We run with --puppetstrings so that we get non-buffered output that we can
        actually read when show_activity=True.

        Args:
            source: A Disk or Image object.
            target: A Disk object (including a Disk from a mounted Image)
            erase:  Whether to erase the target. Defaults to True.
            verify: Whether to verify the clone operation. Defaults to True.
            show_activity: whether to print the progress to the screen.
        Returns:
            boolean: whether the operation succeeded.
        Raises:
            MacDiskError: source is not a Disk or Image object
            MacDiskError: target is not a Disk object
        """

        for volume in self.volumes:
            if str(volume.mountpoint) == str(target):
                imaging_target = volume
                self.workVolume = volume
                break

        if isinstance(imaging_target, macdisk.Disk):
            target_ref = "/dev/%s" % imaging_target.deviceidentifier
        else:
            raise macdisk.MacDiskError("target is not a Disk object")

        command = ["/usr/sbin/asr", "restore", "--source", str(source),
                   "--target", target_ref, "--noprompt", "--puppetstrings"]

        if erase:
            # check we can unmount the target... may as well fail here than later.
            if imaging_target.Mounted():
                imaging_target.Unmount()
            command.append("--erase")

        if not verify:
            command.append("--noverify")

        self.updateProgressTitle_Percent_Detail_('Restoring %s' % source, -1, '')

        NSLog(str(command))
        task = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        message = ""
        while task.poll() is None:
            output = task.stdout.readline().strip()
            try:
                percent = int(output.split("\t")[1])
            except:
                percent = 0.001
            if len(output.split("\t")) == 4:
                if output.split("\t")[3] == "restore":
                    message = "Restoring: "+ str(percent) + "%"
                elif output.split("\t")[3] == "verify":
                    message = "Verifying: "+ str(percent) + "%"
                else:
                    message = ""
            else:
                message = ""
            if percent == 0:
                percent = 0.001
            self.updateProgressTitle_Percent_Detail_(None, percent, message)

        (unused_stdout, stderr) = task.communicate()

        if task.returncode:
            self.errorMessage = "Cloning Error: %s" % stderr
        if task.poll() == 0:
            return True

    def downloadAndInstallPackages(self):
        self.updateProgressTitle_Percent_Detail_('Installing packages...', -1, '')
        # mount the target
        if not self.workVolume.Mounted():
            self.workVolume.Mount()

        pkgs_to_install = [item for item in self.selectedWorkflow['components']
                           if item.get('type') == 'package' and item.get('pre_first_boot')]
        for item in pkgs_to_install:
            package_name = os.path.basename(item['url'])
            self.downloadAndInstallPackage(
                item['url'], self.workVolume.mountpoint,
                progress_method=self.updateProgressTitle_Percent_Detail_)

    def downloadAndInstallPackage(self, url, target, progress_method=None):
        if os.path.basename(url).endswith('.dmg'):
            error = None
            # We're going to mount the dmg
            try:
                dmgmountpoints = Utils.mountdmg(url)
                dmgmountpoint = Utils.dmgmountpoints[0]
            except:
                self.errorMessage = "Couldn't mount %s" % url
                return False

            # Now we're going to go over everything that ends .pkg or
            # .mpkg and install it
            for package in os.listdir(dmgmountpoint):
                if package.endswith('.pkg') or package.endswith('.mpkg'):
                    pkg = os.path.join(dmgmountpoint, package)
                    retcode = self.installPkg(pkg, target, progress_method=progress_method)
                    if retcode != 0:
                        self.errorMessage = "Couldn't install %s" % pkg
                        return False

            # Unmount it
            try:
                Utils.unmountdmg(dmgmountpoint)
            except:
                self.errorMessage = "Couldn't unmount %s" % dmgmountpoint
                return False

        if os.path.basename(url).endswith('.pkg'):

            # Make our temp directory on the target
            temp_dir = tempfile.mkdtemp(dir=target)
            # Download it
            packagename = os.path.basename(url)
            (downloaded_file, error) = Utils.downloadChunks(url, os.path.join(temp_dir,
                                                            packagename))
            if error:
                self.errorMessage = "Couldn't download - %s %s" % (url, error)
                return None
            # Install it
            retcode = self.installPkg(downloaded_file, target, progress_method=progress_method)
            if retcode != 0:
                self.errorMessage = "Couldn't install %s" % pkg
                return None
            # Clean up after ourselves
            shutil.rmtree(temp_dir)

    def downloadAndCopyPackages(self):
        self.updateProgressTitle_Percent_Detail_(
            'Copying packages for install on first boot...', -1, '')
        # mount the target
        if not self.workVolume.Mounted():
            self.workVolume.Mount()

        pkgs_to_install = [item for item in self.selectedWorkflow['components']
                           if item.get('type') == 'package' and not item.get('pre_first_boot')]
        package_count = len(pkgs_to_install)
        counter = 0.0
        # download packages to /usr/local/first-boot - prepend number
        for item in pkgs_to_install:
            counter = counter + 1.0
            package_name = os.path.basename(item['url'])
            (output, error) = self.downloadPackage(item['url'], self.workVolume.mountpoint, counter,
                                  progress_method=self.updateProgressTitle_Percent_Detail_)
            if error:
                self.errorMessage = "Error copying first boot package %s - %s" % (item['url'], error)
                break
        if package_count:
            # copy bits for first boot script
            packages_dir = os.path.join(self.workVolume.mountpoint, 'usr/local/first-boot/')
            if not os.path.exists(packages_dir):
                os.makedirs(packages_dir)
            Utils.copyFirstBoot(self.workVolume.mountpoint)

    def downloadPackage(self, url, target, number, progress_method=None):
        error = None
        dest_dir = os.path.join(target, 'usr/local/first-boot/packages')
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        if os.path.basename(url).endswith('.dmg'):
            NSLog("Copying pkg(s) from %@", url)
            (output, error) = self.copyPkgFromDmg(url, dest_dir, number)
        else:
            NSLog("Downloading pkg %@", url)
            package_name = "%03d-%s" % (number, os.path.basename(url))
            os.umask(0002)
            file = os.path.join(dest_dir, package_name)
            (output, error) = Utils.downloadChunks(url, file, progress_method=progress_method)

        return output, error

    def copyPkgFromDmg(self, url, dest_dir, number):
        error = None
        # We're going to mount the dmg
        try:
            dmgmountpoints = Utils.mountdmg(url)
            dmgmountpoint = Utils.dmgmountpoints[0]
        except:
            self.errorMessage = "Couldn't mount %s" % url
            return False

        # Now we're going to go over everything that ends .pkg or
        # .mpkg and install it
        pkg_list = []
        for package in os.listdir(dmgmountpoint):
            if package.endswith('.pkg') or package.endswith('.mpkg'):
                pkg = os.path.join(dmgmountpoint, package)
                dest_file = os.path.join(dest_dir, "%03d-%s" % (number, os.path.basename(pkg)))
                try:
                    if os.path.isfile(pkg):
                        shutil.copy(pkg, dest_file)
                    else:
                        shutil.copytree(pkg, dest_file)
                except:
                    error = "Couldn't copy %s" % pkg
                    return None, error
                pkg_list.append(dest_file)

        # Unmount it
        try:
            Utils.unmountdmg(dmgmountpoint)
        except:
            self.errorMessage = "Couldn't unmount %s" % dmgmountpoint
            return False

        return pkg_list, None

    def copyFirstBootScripts(self):
        if not self.workVolume.Mounted():
            self.workVolume.Mount()

        scripts_to_run = [item for item in self.selectedWorkflow['components']
                           if item.get('type') == 'script' and not item.get('pre_first_boot')]
        script_count = len(scripts_to_run)
        counter = 0.0
        NSLog(str(scripts_to_run))
        for item in scripts_to_run:
            counter = counter + 1.0
            script = item['content']
            try:
                self.copyScript(
                    script, self.workVolume.mountpoint, counter,
                    progress_method=self.updateProgressTitle_Percent_Detail_)
            except:
                self.errorMessage = "Coun't copy script %s" % str(counter)
                break
        if scripts_to_run:
            Utils.copyFirstBoot(self.workVolume.mountpoint)

    def runPreFirstBootScript(self):
        self.updateProgressTitle_Percent_Detail_(
            'Preparing to run scripts...', -1, '')
        # mount the target
        if not self.workVolume.Mounted():
            self.workVolume.Mount()
        scripts_to_run = [item for item in self.selectedWorkflow['components']
                           if item.get('type') == 'script' and item.get('pre_first_boot')]
        script_count = len(scripts_to_run)
        counter = 0.0
        for item in scripts_to_run:
            script = item['content']
            counter = counter + 1.0
            retcode = self.runScript(
                script, self.workVolume.mountpoint,
                progress_method=self.updateProgressTitle_Percent_Detail_)
            if retcode != 0:
                self.errorMessage = "Script %s returned a non-0 exit code" % str(int(counter))
                break

    def runScript(self, script, target, progress_method=None):
        """
        Replaces placeholders in a script and then runs it.
        """
        # replace the placeholders in the script
        script = Utils.replacePlaceholders(script, target)
        NSLog("Running script on %@", target)
        NSLog("Script: %@", script)
        if progress_method:
            progress_method("Running script...", 0, '')
        proc = subprocess.Popen(script, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        while proc.poll() is None:
            output = proc.stdout.readline().strip().decode('UTF-8')
            if progress_method:
                progress_method(None, None, output)

        return proc.returncode

    def copyScript(self, script, target, number, progress_method=None):
        """
        Copies a
         script to a specific volume
        """
        NSLog("Copying script to %@", target)
        NSLog("Script: %@", script)
        dest_dir = os.path.join(target, 'usr/local/first-boot/scripts')
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        dest_file = os.path.join(dest_dir, "%03d" % number)
        if progress_method:
            progress_method("Copying script to %s" % dest_file, 0, '')
        # convert placeholders
        script = Utils.replacePlaceholders(script, target)
        # write file
        with open(dest_file, "w") as text_file:
            text_file.write(script)
        # make executable
        os.chmod(dest_file, 0755)
        return dest_file

    @objc.IBAction
    def restartButtonClicked_(self, sender):
        NSLog("Restart Button Clicked")
        self.restartToImagedVolume()

    def restartToImagedVolume(self):
        # set the startup disk to the restored volume
        if self.blessTarget == True:
            self.workVolume.SetStartupDisk()
        if self.restartAction == 'restart':
            cmd = ['/sbin/reboot']
        elif self.restartAction == 'shutdown':
            cmd = ['/sbin/shutdown', '-h', 'now']
        task = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        task.communicate()

    def openEndWorkflowPanel(self):
        label_string = "%s completed." % self.selectedWorkflow['name']
        alert = NSAlert.alertWithMessageText_defaultButton_alternateButton_otherButton_informativeTextWithFormat_(
            NSLocalizedString(label_string, None),
            NSLocalizedString(u"Restart", None),
            NSLocalizedString(u"Run another workflow", None),
            NSLocalizedString(u"Shutdown", None),
            NSLocalizedString(u"", None),)

        alert.beginSheetModalForWindow_modalDelegate_didEndSelector_contextInfo_(
            self.mainWindow, self, self.endWorkflowAlertDidEnd_returnCode_contextInfo_, objc.nil)

    @PyObjCTools.AppHelper.endSheetMethod
    def endWorkflowAlertDidEnd_returnCode_contextInfo_(self, alert, returncode, contextinfo):
        # -1 = Shutdown
        # 0 = another workflow
        # 1 = Restart
        if returncode == -1:
            self.restartAction = 'shutdown'
            self.restartToImagedVolume()
        elif returncode == 1:
            self.restartAction = 'restart'
            self.restartToImagedVolume()
        elif returncode == 0:
            self.chooseWorkflowDropDown.setEnabled_(True)
            self.reloadWorkflowsButton.setEnabled_(True)
            self.reloadWorkflowsMenuItem.setEnabled_(True)
            self.chooseImagingTarget_(contextinfo)

    def enableAllButtons_(self, sender):
        self.cancelAndRestartButton.setEnabled_(True)
        self.runWorkflowButton.setEnabled_(True)

    def disableAllButtons(self, sender):
        self.cancelAndRestartButton.setEnabled_(False)
        self.runWorkflowButton.setEnabled_(False)

    @objc.IBAction
    def runDiskUtility_(self, sender):
        Utils.launchApp("/Applications/Utilities/Disk Utility.app")

    @objc.IBAction
    def runTerminal_(self, sender):
        Utils.launchApp("/Applications/Utilities/Terminal.app")

    @objc.IBAction
    def runUtilityFromMenu_(self, sender):
        app_name = sender.title()
        app_path = os.path.join('/Applications/Utilities/', app_name + '.app')
        if os.path.exists(app_path):
            Utils.launchApp(app_path)

    def buildUtilitiesMenu(self):
        self.utilities_menu.removeAllItems()
        for item in os.listdir('/Applications/Utilities'):
            if item.endswith('.app'):
                item_name = os.path.splitext(item)[0]
                new_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    item_name, self.runUtilityFromMenu_, u'')
                new_item.setTarget_(self)
                self.utilities_menu.addItem_(new_item)

    def installPkg(self, pkg, target, progress_method=None):
        """
        Installs a package on a specific volume
        """
        NSLog("Installing %@ to %@", pkg, target)
        if progress_method:
            progress_method("Installing %s" % os.path.basename(pkg), 0, '')
        cmd = ['/usr/sbin/installer', '-pkg', pkg, '-target', target, '-verboseR']
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while proc.poll() is None:
            output = proc.stdout.readline().strip().decode('UTF-8')
            if output.startswith("installer:"):
                msg = output[10:].rstrip("\n")
                if msg.startswith("PHASE:"):
                    phase = msg[6:]
                    if phase:
                        NSLog(phase)
                        if progress_method:
                            progress_method(None, None, phase)
                elif msg.startswith("STATUS:"):
                    status = msg[7:]
                    if status:
                        NSLog(status)
                        if progress_method:
                            progress_method(None, None, status)
                elif msg.startswith("%"):
                    percent = float(msg[1:])
                    NSLog("%@ percent complete", percent)
                    if progress_method:
                        progress_method(None, percent, None)
                elif msg.startswith(" Error"):
                    NSLog(msg)
                    if progress_method:
                        progress_method(None, None, msg)
                elif msg.startswith(" Cannot install"):
                    NSLog(msg)
                    if progress_method:
                        progress_method(None, None, msg)
                else:
                    NSLog(msg)
                    if progress_method:
                        progress_method(None, None, msg)

        return proc.returncode
    
    def shakeWindow(self):
        shake = {'count': 1, 'duration': 0.3, 'vigor': 0.04}
        shakeAnim = Quartz.CAKeyframeAnimation.animation()
        shakePath = Quartz.CGPathCreateMutable()
        frame = self.mainWindow.frame()
        Quartz.CGPathMoveToPoint(shakePath, None, NSMinX(frame), NSMinY(frame))
        shakeLeft = NSMinX(frame) - frame.size.width * shake['vigor']
        shakeRight = NSMinX(frame) + frame.size.width * shake['vigor']
        for i in range(shake['count']):
            Quartz.CGPathAddLineToPoint(shakePath, None, shakeLeft, NSMinY(frame))
            Quartz.CGPathAddLineToPoint(shakePath, None, shakeRight, NSMinY(frame))
            Quartz.CGPathCloseSubpath(shakePath)
        shakeAnim._['path'] = shakePath
        shakeAnim._['duration'] = shake['duration']
        self.mainWindow.setAnimations_(NSDictionary.dictionaryWithObject_forKey_(shakeAnim, "frameOrigin"))
        self.mainWindow.animator().setFrameOrigin_(frame.origin)
