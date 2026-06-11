//
//  LaunchView.swift
//  MyHerzen
//
//  Created by Nicolas Forest on 10/1/25.
//

import SwiftUI

struct LaunchView: View {
    @State private var showContent = false
    @State private var animateGlass = false
    @State private var showLogo = false
    @ObservedObject var viewModel: ScheduleViewModel
    var body: some View {
        if showContent {
            ContentView(viewModel: viewModel)
        } else {
            ZStack {
#if os(iOS)
                Color(.systemBackground).ignoresSafeArea()
#elseif os(macOS)
                Color(NSColor.windowBackgroundColor).ignoresSafeArea()
#endif
                ZStack {
                    VStack(spacing: 12) {
                        Image("herzenicon") // замените на логотип
                            .resizable()
                            .frame(width: 200, height: 200)
                            .foregroundColor(.white)
                            .opacity(showLogo ? 1 : 0)
                            .animation(.easeIn(duration: 0.5), value: showLogo)

                        Text("Добро пожаловать")
                            .font(.system(size: 32, weight: .bold))
                            .foregroundColor(Color(hex: "264796"))
                            .opacity(showLogo ? 1 : 0)
                            .animation(.easeIn(duration: 0.5), value: showLogo)

                        Text("в Твой Герцена")
                            .font(.system(size: 24))
                            .foregroundColor(Color(hex: "264796"))
                            .opacity(showLogo ? 1 : 0)
                            .animation(.easeIn(duration: 0.5), value: showLogo)
                    }
                    VStack {
                        Spacer()
                                          
                        Text("При поддержке Flash Up Energy")
                            .font(.system(size: 12))
                            .foregroundColor(Color(hex: "264796"))
                            .opacity(showLogo ? 1 : 0)
                            .animation(.easeIn(duration: 0.5), value: showLogo)
                            .padding(.bottom, 20)
                        
                        Text("Версия 0.9 альфа")
                            .font(.system(size: 12))
                            .foregroundColor(Color(hex: "264796"))
                            .opacity(showLogo ? 1 : 0)
                            .animation(.easeIn(duration: 0.5), value: showLogo)
                            .padding(.bottom, 20)
                    }
                }
            }
            .onAppear {
                showLogo = true
                Task {
                    await UserSettingsSyncService.syncRemoteSettingsIfAuthenticated()
                }
                DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                    withAnimation {
                        showContent = true
                    }
                }
            }
        }
    }
}

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255,
                            (int >> 8) * 17,
                            (int >> 4 & 0xF) * 17,
                            (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255,
                            int >> 16,
                            int >> 8 & 0xFF,
                            int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24,
                            int >> 16 & 0xFF,
                            int >> 8 & 0xFF,
                            int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue:  Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}
