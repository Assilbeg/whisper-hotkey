import CoreGraphics

let src = CGEventSource(stateID: .hidSystemState)

// Relâche tous les modificateurs d'abord
let clear = CGEvent(keyboardEventSource: src, virtualKey: 0, keyDown: false)!
clear.flags = []
clear.post(tap: .cghidEventTap)

// Cmd+V avec le vrai keycode physique (9 = touche V)
let vDown = CGEvent(keyboardEventSource: src, virtualKey: 9, keyDown: true)!
vDown.flags = .maskCommand
vDown.post(tap: .cghidEventTap)

let vUp = CGEvent(keyboardEventSource: src, virtualKey: 9, keyDown: false)!
vUp.flags = .maskCommand
vUp.post(tap: .cghidEventTap)
