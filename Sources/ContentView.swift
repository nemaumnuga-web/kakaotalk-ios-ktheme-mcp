import SwiftUI

struct ContentView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "paintbrush.fill")
                .font(.system(size: 64))
                .foregroundStyle(.yellow)
            Text("KTheme")
                .font(.largeTitle.bold())
            Text("빌드가 정상적으로 설치되었습니다.")
                .foregroundStyle(.secondary)
        }
        .padding()
    }
}

#Preview {
    ContentView()
}
