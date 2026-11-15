Rar-Converter - Windows EXE Build Package
================================================

This package includes a GitHub Actions workflow that builds the Windows EXE
on a real Windows runner. The resulting EXE does not require Python on VA PCs.

BUILD THE EXE USING GITHUB (NO PYTHON INSTALL NEEDED ON YOUR PC)
1. Create a GitHub account if you do not already have one.
2. Create a NEW repository, e.g. gichu-rar-converter.
3. Upload the contents of this ZIP to the repository, including the hidden
   .github folder and its workflows/build-windows.yml file.
   IMPORTANT: Make sure the .github folder is included.
4. Open the repository's Actions tab.
5. Select "Build Windows EXE" on the left.
6. Click "Run workflow" if it has not started automatically after the upload.
7. Wait for the workflow to finish successfully.
8. Open the completed workflow run and download the artifact named
   "Rar-Converter-Windows".
9. Extract that artifact ZIP. It contains:
   Rar-Converter.exe

TEAM REQUIREMENTS
- Windows 10/11.
- WinRAR installed, because the app uses WinRAR's rar.exe to create genuine RAR files.
- Python is NOT required on team members' computers.

APP SAFETY / BEHAVIOR
- Original folders are kept unchanged.
- The first word of the first non-empty line in GhiChu becomes the archive name.
- It searches recursively for a file named GhiChu (extension optional).
- Existing archive names are not overwritten; duplicates get _2, _3, etc.
- Missing or unreadable GhiChu files are reported in the scan list.

ALTERNATIVE LOCAL BUILD
On a Windows build PC with Python 3 installed, run Build_Windows_EXE.bat.
The EXE will appear in the dist folder.

NOTE
This environment cannot execute a Windows build itself. The included GitHub
Actions workflow performs the actual compilation on a Windows machine in the
cloud and provides the finished EXE as a downloadable build artifact.
