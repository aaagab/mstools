#!/usr/bin/env python3
from __future__ import print_function
import json
from pprint import pprint
import os
import re
import shlex
import subprocess
import sys
import threading

import ctypes
if os.name == "nt":
    from ctypes import wintypes, c_char_p
from collections import namedtuple

class Windows():
    def __init__(self, debug=False):
        self.debug=debug

        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        if not hasattr(wintypes, 'LPDWORD'): # PY2
            wintypes.LPDWORD = ctypes.POINTER(wintypes.DWORD)

        self.WindowInfo = namedtuple('WindowInfo', 'pid title')

        self.WNDENUMPROC = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HWND,    # _In_ hWnd
            wintypes.LPARAM,) # _In_ lParam

        self.user32.EnumWindows.errcheck = self.check_zero
        self.user32.EnumWindows.argtypes = (
        self.WNDENUMPROC,      # _In_ lpEnumFunc
        wintypes.LPARAM,) # _In_ lParam

        self.user32.IsWindowVisible.argtypes = (
            wintypes.HWND,) # _In_ hWnd

        self.user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user32.GetWindowThreadProcessId.argtypes = (
        wintypes.HWND,     # _In_      hWnd
        wintypes.LPDWORD,) # _Out_opt_ lpdwProcessId

        self.user32.GetWindowTextLengthW.errcheck = self.check_zero
        self.user32.GetWindowTextLengthW.argtypes = (
        wintypes.HWND,) # _In_ hWnd

        self.user32.GetWindowTextW.errcheck = self.check_zero
        self.user32.GetWindowTextW.argtypes = (
            wintypes.HWND,   # _In_  hWnd
            wintypes.LPWSTR, # _Out_ lpString
            ctypes.c_int,)   # _In_  nMaxCount

    def check_zero(self, result, func, args):    
        if not result:
            err = ctypes.get_last_error()
            if err:
                raise ctypes.WinError(err)
        return args

    def list_windows(self):
        '''Return a sorted list of visible windows.'''
        result = []
        @self.WNDENUMPROC
        def enum_proc(hwnd, lParam):
            if self.user32.IsWindowVisible(hwnd):
                pid = wintypes.DWORD()
                tid = self.user32.GetWindowThreadProcessId(
                            hwnd, ctypes.byref(pid))
                length = self.user32.GetWindowTextLengthW(hwnd) + 1
                title = ctypes.create_unicode_buffer(length)
                self.user32.GetWindowTextW(hwnd, title, length)

                result.append(dict(
                    title=title.value,
                    hwnd=hwnd,
                    pid=pid.value,
                ))
            return True
        self.user32.EnumWindows(enum_proc, 0)
        # return sorted(result)
        return result

    def focus(self, pid):
        found=False
        for window in self.list_windows():
            if self.debug is True:
                print(window)
            if window["pid"] == int(pid):
                found=True
                self.show_window(window["hwnd"])
                self.user32.SetForegroundWindow(window["hwnd"])
                break
        if found is False:
            print("No Window Found for pid '{}'".format(pid))

    def rename(self, pid, title):
        found=False
        for window in self.list_windows():
            if self.debug is True:
                print(window)
            if window["pid"] == int(pid):
                found=True
                self.user32.SetWindowTextA(window["hwnd"], c_char_p(title.encode()))
                break
        if found is False:
            print("No Window Found for pid '{}'".format(pid))

    def show_window(self, hwnd):
        SW_RESTORE=9
        SW_SHOW=5
        SW_SHOWNORMAL=1
        if self.user32.IsIconic(hwnd): # if minized, restore
            self.user32.ShowWindow(hwnd, SW_RESTORE)

    def get_active(self):
        h_wnd = self.user32.GetForegroundWindow()
        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(h_wnd, ctypes.byref(pid))
        return pid.value


# To minimize a window you need to know either the title of the window, or its window class. The window class is useful when the exact window title is not known. For example the following script shows two different ways to minimize the Microsoft Windows Notepad application assuming:
# import ctypes
# notepad_handle = ctypes.windll.user32.FindWindowW(None, "Untitled - Notepad")
# ctypes.windll.user32.ShowWindow(notepad_handle, 6)
# notepad_handle = ctypes.windll.user32.FindWindowW(u"Notepad", None) 
# ctypes.windll.user32.ShowWindow(notepad_handle, 6)  
# To determine the class name to use, you would need to use an tool such as Microsoft's Spy++. Obviously if Notepad was opened with a file, it would have a different title such as test.txt - Notepad. If this was the case, the first example would now fail to find the window, but the second example would still work.
# If two copies of notepad were running, then only one would be closed. If all copies needed to be closed, you would need to enumerate all windows which requires more code.
# The ShowWindow command can also be used to restore the Window. The 6 used here is the Windows code for SW_MINIMIZE.
