# Installing Crowdstrike Falcon Protect for MacOS via Microsoft Intune
Intune doesn't support installing .pkg files directly - instead requiring wrapping them using custom scripts.

It's much easier and more reliable to use a shell script to deploy Crowdstrike Falcon Protect to end-users.

Here's the steps I went through to get it working.

## Step 1 - Deploy configuration profiles
Crowdstrike provides a Configuration profile to enable KExts, System Extensions, Full Disk Access and Web Content Filtering that can be deployed by Intune. Unfortunately this profile does not work on Apple Silicon (M1) devices due to lack of support for KExts.

This would be an easy fix if there was a way to identify arm64 devices in intune for use in Dynamic Groups or the new Filters feature - but so far I haven't figured out a decent way to do this (If you find something, please submit an issue or PR on this repo!).

The closest thing to do to get this to work is to deploy two .mobileconfigs - one with the standalone kexts and one with the rest of the permissions - the kexts will still fail on Apple Silicon, but it doesn't cause any issues with the installation, since Crowdstrike doesn't try to use them on M1.

Deploy the .mobileconfig files in /MobileConfigs by doing the following:

1) Open open the Microsoft Endpoint Manager admin center

2) Select Devices -> Configuration Profiles

3) Click Create Profile

4) In the blade that opens on the right, select macOS for platform, Templates for Profile type, and Custom for template name. Click Create

5) Enter the basic details for the profile. Click Next

6) Upload [MobileConfigs/Falcon Profile.mobileconfig](https://supportportal.crowdstrike.com/s/article/ka16T000000wtMWQAY)

7) Choose the users and/or devices to deploy to

8) Review the settings for your profile, and click Create
