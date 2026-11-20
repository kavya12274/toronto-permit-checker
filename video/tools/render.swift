// Makes the demo video: draws video/demo.html frame by frame (30 frames a second), then adds your voice.
//
// Run it (the app must be running: python3 app.py), from the project folder:
//     swift video/tools/render.swift
// Result: video/output/permit_precheck_demo.mp4
//
// Uses only what comes with macOS (WebKit to draw the page, AVFoundation to make the video).
// It doesn't record your screen: it asks the page to jump to each moment and takes a picture of it,
// so every frame lines up exactly with your voice and no Screen Recording permission is needed.

import AppKit
import AVFoundation
import WebKit

let width = 1920, height = 1080, fps: Int32 = 30
let here = URL(fileURLWithPath: CommandLine.arguments[0]).deletingLastPathComponent()
let videoDir = here.deletingLastPathComponent()
let outDir = videoDir.appendingPathComponent("output")
let silentURL = outDir.appendingPathComponent("frames_only.mp4")
let finalURL = outDir.appendingPathComponent("permit_precheck_demo.mp4")
let voiceURL = videoDir.appendingPathComponent("audio/voice.m4a")
let pageURL = URL(string: "http://localhost:8010/video/demo.html?render=1")!

func say(_ s: String) { FileHandle.standardError.write((s + "\n").data(using: .utf8)!) }

@MainActor
final class Renderer: NSObject {
    let window: NSWindow
    let web: WKWebView

    override init() {
        let config = WKWebViewConfiguration()
        config.mediaTypesRequiringUserActionForPlayback = .all
        web = WKWebView(frame: NSRect(x: 0, y: 0, width: width, height: height), configuration: config)
        web.appearance = NSAppearance(named: .aqua)          // light mode, whatever the Mac is set to
        window = NSWindow(contentRect: NSRect(x: -4000, y: -4000, width: width, height: height),
                          styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = web
        window.orderFrontRegardless()                          // placed off screen, so you won't see it
        super.init()
    }

    func js(_ code: String, _ args: [String: Any] = [:]) async throws -> Any? {
        try await web.callAsyncJavaScript(code, arguments: args, in: nil, contentWorld: .page)
    }

    func run() async throws {
        try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)
        try? FileManager.default.removeItem(at: silentURL)
        try? FileManager.default.removeItem(at: finalURL)

        say("Loading the demo page…")
        web.load(URLRequest(url: pageURL))
        var ready = false
        for _ in 0..<300 {                                      // wait up to 30 s
            try await Task.sleep(nanoseconds: 100_000_000)
            if let r = try? await js("return window.demoReady === true"), (r as? Bool) == true { ready = true; break }
        }
        guard ready else { throw NSError(domain: "render", code: 1, userInfo: [NSLocalizedDescriptionKey:
            "The demo page didn't load. Is the app running (python3 app.py)?"]) }
        let duration = (try await js("return window.DURATION") as? Double) ?? 51.2

        // Video writer
        let writer = try AVAssetWriter(outputURL: silentURL, fileType: .mp4)
        let input = AVAssetWriterInput(mediaType: .video, outputSettings: [
            AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: width, AVVideoHeightKey: height,
            AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: 10_000_000, AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel]])
        input.expectsMediaDataInRealTime = false
        let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
            kCVPixelBufferWidthKey as String: width, kCVPixelBufferHeightKey as String: height])
        writer.add(input)
        writer.startWriting()
        writer.startSession(atSourceTime: .zero)

        let snap = WKSnapshotConfiguration()
        snap.rect = NSRect(x: 0, y: 0, width: width, height: height)
        snap.afterScreenUpdates = true

        let frames = Int((duration * Double(fps)).rounded(.up))
        say("Drawing \(frames) frames…")
        for i in 0..<frames {
            let t = Double(i) / Double(fps)
            _ = try await js("return await window.seekTo(t)", ["t": t])
            let image = try await web.takeSnapshot(configuration: snap)
            guard let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
            while !input.isReadyForMoreMediaData { try await Task.sleep(nanoseconds: 5_000_000) }
            guard let pool = adaptor.pixelBufferPool else { throw NSError(domain: "render", code: 2) }
            var buffer: CVPixelBuffer?
            CVPixelBufferPoolCreatePixelBuffer(nil, pool, &buffer)
            guard let pb = buffer else { continue }
            CVPixelBufferLockBaseAddress(pb, [])
            let ctx = CGContext(data: CVPixelBufferGetBaseAddress(pb), width: width, height: height, bitsPerComponent: 8,
                                bytesPerRow: CVPixelBufferGetBytesPerRow(pb), space: CGColorSpaceCreateDeviceRGB(),
                                bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue)!
            ctx.interpolationQuality = .high
            ctx.draw(cg, in: CGRect(x: 0, y: 0, width: width, height: height))
            CVPixelBufferUnlockBaseAddress(pb, [])
            adaptor.append(pb, withPresentationTime: CMTime(value: CMTimeValue(i), timescale: fps))
            if i % 150 == 0 { say(String(format: "  %.0f%% (%.1f s)", Double(i) / Double(frames) * 100, t)) }
        }
        input.markAsFinished()
        await writer.finishWriting()
        if writer.status != .completed { throw writer.error ?? NSError(domain: "render", code: 3) }

        // Add your voice
        say("Adding your voice…")
        let comp = AVMutableComposition()
        let videoAsset = AVURLAsset(url: silentURL), voiceAsset = AVURLAsset(url: voiceURL)
        let vTrack = try await videoAsset.loadTracks(withMediaType: .video)[0]
        let aTrack = try await voiceAsset.loadTracks(withMediaType: .audio)[0]
        let vDur = try await videoAsset.load(.duration), aDur = try await voiceAsset.load(.duration)
        let dur = CMTimeMinimum(vDur, aDur)
        let cv = comp.addMutableTrack(withMediaType: .video, preferredTrackID: kCMPersistentTrackID_Invalid)!
        try cv.insertTimeRange(CMTimeRange(start: .zero, duration: dur), of: vTrack, at: .zero)
        let ca = comp.addMutableTrack(withMediaType: .audio, preferredTrackID: kCMPersistentTrackID_Invalid)!
        try ca.insertTimeRange(CMTimeRange(start: .zero, duration: dur), of: aTrack, at: .zero)
        guard let export = AVAssetExportSession(asset: comp, presetName: AVAssetExportPresetPassthrough) else {
            throw NSError(domain: "render", code: 4) }
        export.outputURL = finalURL
        export.outputFileType = .mp4
        await export.export()
        if export.status != .completed { throw export.error ?? NSError(domain: "render", code: 5) }
        try? FileManager.default.removeItem(at: silentURL)
        say("Done: \(finalURL.path)")
    }
}

let app = NSApplication.shared
app.setActivationPolicy(.accessory)
Task { @MainActor in
    do { try await Renderer().run(); exit(0) }
    catch { say("Error: \(error.localizedDescription)"); exit(1) }
}
app.run()
