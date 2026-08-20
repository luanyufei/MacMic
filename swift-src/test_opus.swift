import Foundation
import COpus

let sampleRate: Int32 = 48000
let channels: Int32 = 1
var err: Int32 = 0

if let decoder = opus_decoder_create(sampleRate, channels, &err) {
    print("✅ Opus decoder created successfully in Swift!")
    opus_decoder_destroy(decoder)
} else {
    print("❌ Failed with error: \(err)")
}
