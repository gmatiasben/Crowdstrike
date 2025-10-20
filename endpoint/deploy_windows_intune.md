# Installing the CrowdStrike Falcon Sensor using Microsoft Intune

This guide provides step-by-step instructions for installing the CrowdStrike Falcon Sensor by using Microsoft Intune. This deployment method provides centralized management and automated distribution of the CrowdStrike Falcon Sensor across your organization's Windows devices.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Downloading the falcon sensor](#downloading-the-falcon-sensor)
- [Creating a .intunewim Package](#creating-a-intunewim-package-for-microsoft-intune)
- [Configuring the Application in Microsoft Intune](#configuring-the-application-in-microsoft-intune)
- [Deployment and Monitoring](#deployment-and-monitoring)
- [Troubleshooting](#troubleshooting)

## Prerequisites

> [!IMPORTANT]
> 
> The following are the required prerequisites to deploy CrowdStrike Falcon sensors using Microsoft Intune:
> - Microsoft Intune subscription with appropriate licenses
> - Administrative access to the Microsoft Intune console
> - The [Microsoft Win32 Content Prep Tool](https://github.com/microsoft/Microsoft-Win32-Content-Prep-Tool) installed on your system

## Downloading the Falcon Sensor

The CrowdStrike Falcon Sensor for Windows is available for download directly within the Falcon Console. This can be found by navigating to Host setup and management → Sensor downloads.

Take note of your Customer ID. This identifier is unique to your organization and is required during deployment to link each individual Sensor deployed to your individual instance of CrowdStrike Falcon.

### Downloading the Falcon Uninstall Tool (optional)

The software package created in the steps ahead can be used for installation and removal of the sensor through Microsoft Intune. If you do not wish to use the same package for both installation and removal, skip this step. The Windows Sensor Uninstall Tool is available for download directly within the Falcon Console. This can be found by navigating to Support → Tool Downloads. 

The Falcon Windows Sensor Uninstall Tool is found at the bottom of the page.

## Creating a .intunewim Package for Microsoft Intune

1. Download the tool from GitHub: [Microsoft Win32 Content Prep Tool](https://github.com/microsoft/Microsoft-Win32-Content-Prep-Tool/raw/refs/heads/master/IntuneWinAppUtil.exe)
2. On a Windows system, create a dedicated folder that will be used to compress the installation files into the `.intunewim` (e.g., `C:\Falcon\`)
3. Place the `FalconSensor_Windows.exe` installer into this folder

> [!NOTE]
> Please be aware that the entire contents of the selected folder will be archived during the conversion process.

4. Open the **Command Prompt** as Administrator
5. Run `IntuneWinAppUtil.exe` and follow the interactive prompts. For example:

```console
Please specify the source folder: C:\Falcon
Please specify the setup file: FalconSensor_Windows.exe
Please specify the output folder: C:\IntuneFiles
Do you want to specify catalog folder (Y/N)? n
```

When `IntuneWinAppUtil.exe` has finished archiving the contents of the source folder, you'll find the new `.intunewim` file in your specified output folder.

## Configuring the Application in Microsoft Intune

### Creating the Application

1. In the Microsoft Intune admin center, navigate to **Apps → All Apps → Create**
2. Under **App Type**, select **Windows App (Win32)**
3. In the Add App Pane, click **Select app package file**, and select the `.intunewim` file you created

### App Information

Configure the basic application details:

- **Name:** CrowdStrike Falcon Sensor (or your preferred name)
- **Publisher:** CrowdStrike
- **Description:** Add appropriate description for your organization
- Fill in the other fields as needed according to your organization's guidelines

When complete, click **Next**.

### Program Configuration

Configure the installation and uninstall commands:

**Install Command:**
```cmd
FalconSensor_Windows.exe /install /quiet /norestart CID=YOUR_FALCON_CID
```

**Uninstall Command:**
```cmd
FalconSensor_Windows.exe /uninstall /quiet
```

**Additional Program Settings:**
- **Install Behavior:** System (executes with administrative rights)
- **Device Restart Behavior:** No Specific Action (no reboot required)
- **Return Codes:** Leave as default

> [!IMPORTANT]
> Replace `YOUR_FALCON_CID` with your actual CrowdStrike Falcon Customer ID (CID)

Click **Next** when configuration is complete.

### Requirements

Set the following based on your environment:
- **Operating System Architecture:** Select appropriate architecture
- **Minimum Operating System:** Set according to your requirements

Click **Next** to continue.

### Detection Rules

Configure Intune to detect if the Falcon Sensor is installed:

1. Select **Manually Configure Detection Rules** from the **Rules format** dropdown
2. Click **+ Add**
3. For the **Rule Type**, select **File**
4. Configure the detection parameters:
   - **Path:** `C:\Program Files\CrowdStrike`
   - **File or Folder:** `CSFalconController.exe`
   - **Detection Method:** File or Folder Exists

Click **OK** to save the detection rule, then click **Next**.

### Dependencies and Supersedence

- **Dependencies:** Click **Next** (no dependencies required for standard deployment)
- **Supersedence:** Click **Next** (not applicable for initial deployment)

### Assignments

1. Under **Required**, configure deployment targets:
   - Add individual Asset Groups, or
   - Select All Users to deploy to all managed endpoints
2. Review and confirm all assignment settings

Click **Next** to proceed.

### Review and Create

1. Review all configuration settings for accuracy
2. Verify install commands, detection rules, and assignments
3. Click **Create** to finalize the deployment package

## Deployment and Monitoring

### Deployment Process

After creating the application package:

1. The `.intunewim` file will be uploaded to Intune
2. Wait for notification that the app is ready for deployment
3. The sensor will deploy automatically during the next Intune sync cycle
4. Manual sync can be initiated if immediate deployment is required

### Monitoring Deployment

Monitor the deployment progress through:
- **Apps → All Apps → [Your App Name] → Device install status**
- Review installation success rates and identify any failed deployments
- Check individual device status for troubleshooting specific issues

