import SwiftUI

struct CalendarDatePicker: View {
    @Binding var selectedDate: Date
    var showsChrome = true

    var body: some View {
        DatePicker("", selection: $selectedDate, displayedComponents: .date)
            .datePickerStyle(.compact)
            .labelsHidden()
            .padding(showsChrome ? 8 : 0)
            .background {
                if showsChrome {
                    Color.myherzenHeaderCapsuleFill
                } else {
                    Color.clear
                }
            }
            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }
}
