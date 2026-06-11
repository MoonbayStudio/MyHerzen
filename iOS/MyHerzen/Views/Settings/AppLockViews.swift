import SwiftUI
#if os(iOS)

struct AppLockSetupView: View {
    @ObservedObject var lockManager: AppLockManager
    let onDone: () -> Void

    @State private var passcode = ""
    @State private var confirmation = ""
    @State private var errorMessage: String?

    var body: some View {
        NavigationView {
            VStack(alignment: .leading, spacing: 18) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Код приложения")
                        .font(.title2.weight(.semibold))
                    Text("Код понадобится при открытии приложения. Его можно будет заменить в настройках.")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }

                SecureField("Введите код", text: $passcode)
                    .keyboardType(.numberPad)
                    .textContentType(.oneTimeCode)
                    .myherzenDefaultSurface(cornerRadius: 22, padding: 12)

                SecureField("Повторите код", text: $confirmation)
                    .keyboardType(.numberPad)
                    .textContentType(.oneTimeCode)
                    .myherzenDefaultSurface(cornerRadius: 22, padding: 12)

                if let errorMessage {
                    Text(errorMessage)
                        .font(.caption)
                        .foregroundColor(.red)
                }

                Button {
                    savePasscode()
                } label: {
                    Label("Сохранить код", systemImage: "lock.fill")
                        .frame(maxWidth: .infinity)
                        .myherzenDefaultSurface(cornerRadius: 22, padding: 12)
                }
                .myherzenInteractiveButtonStyle()

                Spacer()
            }
            .padding(20)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Отмена") {
                        onDone()
                    }
                }
            }
        }
    }

    private func savePasscode() {
        let trimmedPasscode = passcode.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedConfirmation = confirmation.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmedPasscode.count >= 4 else {
            errorMessage = "Код должен быть не короче 4 символов."
            return
        }
        guard trimmedPasscode == trimmedConfirmation else {
            errorMessage = "Коды не совпадают."
            return
        }

        do {
            try lockManager.setPasscode(trimmedPasscode)
            onDone()
        } catch {
            errorMessage = "Не удалось сохранить код. Попробуйте ещё раз."
        }
    }
}

struct AppLockGateView: View {
    @ObservedObject var lockManager: AppLockManager
    @State private var passcode = ""
    @State private var errorMessage: String?
    @State private var isAuthenticating = false

    var body: some View {
        ZStack {
            Color(.systemBackground)
                .ignoresSafeArea()

            VStack(spacing: 18) {
                Image(systemName: "lock.fill")
                    .font(.system(size: 34, weight: .semibold))
                    .foregroundColor(.accentColor)

                VStack(spacing: 6) {
                    Text("MyHerzen заблокирован")
                        .font(.title3.weight(.semibold))
                    Text("Введите код приложения")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }

                SecureField("Код", text: $passcode)
                    .keyboardType(.numberPad)
                    .textContentType(.oneTimeCode)
                    .multilineTextAlignment(.center)
                    .font(.title3.weight(.semibold))
                    .padding(12)
                    .background(Color.myherzenHeaderCapsuleFill)
                    .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
                    .onSubmit { unlockWithPasscode() }

                if let errorMessage {
                    Text(errorMessage)
                        .font(.caption)
                        .foregroundColor(.red)
                }

                Button {
                    unlockWithPasscode()
                } label: {
                    Text("Разблокировать")
                        .font(.subheadline.weight(.semibold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(Color.accentColor.opacity(0.16))
                        .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
                }
                .buttonStyle(.plain)

                if lockManager.isBiometryEnabled && lockManager.canUseBiometry {
                    Button {
                        authenticateWithBiometry()
                    } label: {
                        Label(lockManager.biometryTitle, systemImage: lockManager.biometryTitle == "Face ID" ? "faceid" : "touchid")
                            .font(.subheadline.weight(.semibold))
                    }
                    .buttonStyle(.plain)
                    .disabled(isAuthenticating)
                }
            }
            .padding(20)
            .frame(maxWidth: 340)
            .myherzenDefaultSurface(cornerRadius: 22, padding: 18)
            .padding(24)
        }
        .onAppear {
            if lockManager.isBiometryEnabled {
                authenticateWithBiometry()
            }
        }
    }

    private func unlockWithPasscode() {
        guard lockManager.unlock(with: passcode) else {
            errorMessage = "Неверный код."
            passcode = ""
            return
        }
        errorMessage = nil
    }

    private func authenticateWithBiometry() {
        guard !isAuthenticating else { return }
        isAuthenticating = true
        Task {
            let success = await lockManager.authenticateWithBiometry()
            if !success {
                errorMessage = nil
            }
            isAuthenticating = false
        }
    }
}

struct AppLockPrivacyCoverView: View {
    var body: some View {
        ZStack {
            Color(.systemBackground)
                .ignoresSafeArea()

            VStack(spacing: 14) {
                Image(systemName: "lock.fill")
                    .font(.system(size: 34, weight: .semibold))
                    .foregroundColor(.accentColor)
                Text("MyHerzen заблокирован")
                    .font(.title3.weight(.semibold))
            }
            .padding(24)
        }
    }
}
#endif
