// Transcribe an audio file on this Mac (Apple's on-device speech recognition) and print each word with its start time.
// Usage: swift transcribe.swift voice.m4a > words.json
import Foundation
import Speech

let path = CommandLine.arguments[1]
let sem = DispatchSemaphore(value: 0)
SFSpeechRecognizer.requestAuthorization { status in
    guard status == .authorized else { FileHandle.standardError.write("Speech recognition not allowed (\(status.rawValue))\n".data(using: .utf8)!); exit(2) }
    guard let rec = SFSpeechRecognizer(locale: Locale(identifier: "en-CA")), rec.isAvailable else { FileHandle.standardError.write("Recognizer unavailable\n".data(using: .utf8)!); exit(3) }
    let req = SFSpeechURLRecognitionRequest(url: URL(fileURLWithPath: path))
    if rec.supportsOnDeviceRecognition { req.requiresOnDeviceRecognition = true }
    req.shouldReportPartialResults = false
    req.addsPunctuation = true
    rec.recognitionTask(with: req) { result, error in
        if let error = error { FileHandle.standardError.write("Error: \(error)\n".data(using: .utf8)!); exit(4) }
        guard let result = result, result.isFinal else { return }
        let words = result.bestTranscription.segments.map { ["w": $0.substring, "t": $0.timestamp, "d": $0.duration] as [String: Any] }
        let data = try! JSONSerialization.data(withJSONObject: words, options: [])
        print(String(data: data, encoding: .utf8)!)
        sem.signal()
    }
}
sem.wait()
