import SwiftUI

struct ThinkingInputBar: View {
    @Binding var text: String
    let isThinking: Bool
    var isCancelling = false
    let placeholder: String
    let sendSymbolName: String
    var isDisabled = false
    let onSend: () -> Void
    let onCancel: () -> Void
    let themedShape: ThemedComponentShape

    var body: some View {
        ThemedChrome(shape: themedShape) {
            HStack(spacing: 10) {
                TextField(placeholder, text: $text)
                    .textFieldStyle(.plain)
                    .disabled(isDisabled || isThinking)
                    .submitLabel(.send)
                    .onSubmit {
                        submit()
                    }

                Button {
                    isThinking ? onCancel() : submit()
                } label: {
                    Group {
                        if isThinking && !isCancelling {
                            ProgressView()
                                .controlSize(.small)
                        } else {
                            Image(systemName: isThinking ? "xmark" : sendSymbolName)
                                .font(.system(size: 15, weight: .semibold))
                        }
                    }
                    .frame(width: 36, height: 36)
                    .contentShape(Circle())
                }
                .buttonStyle(.plain)
                .disabled(isDisabled || (!isThinking && text.myherzenTrimmed.isEmpty))
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(Color.clear)
        }
    }

    private func submit() {
        guard !text.myherzenTrimmed.isEmpty, !isThinking, !isDisabled else { return }
        onSend()
    }
}
