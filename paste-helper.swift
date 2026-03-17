import CoreGraphics
import AppKit

// Connexion au window server (nécessaire pour poster des events)
let app = NSApplication.shared
app.setActivationPolicy(.accessory)

// Petit délai pour que la connexion s'établisse
Thread.sleep(forTimeInterval: 0.05)

let src = CGEventSource(stateID: .hidSystemState)

// Relâche tous les modificateurs
let clear = CGEvent(keyboardEventSource: src, virtualKey: 0, keyDown: false)!
clear.flags = []
clear.post(tap: .cghidEventTap)

Thread.sleep(forTimeInterval: 0.05)

// Cmd+V avec keycode physique (9 = V)
let vDown = CGEvent(keyboardEventSource: src, virtualKey: 9, keyDown: true)!
vDown.flags = .maskCommand
vDown.post(tap: .cghidEventTap)

Thread.sleep(forTimeInterval: 0.05)

let vUp = CGEvent(keyboardEventSource: src, virtualKey: 9, keyDown: false)!
vUp.flags = .maskCommand
vUp.post(tap: .cghidEventTap)
