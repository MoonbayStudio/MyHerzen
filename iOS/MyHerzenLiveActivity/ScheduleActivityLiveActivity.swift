import ActivityKit
import WidgetKit
import SwiftUI

@available(iOSApplicationExtension 16.1, *)
struct ScheduleActivityLiveActivity: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: ScheduleActivityAttributes.self) { context in
            VStack(alignment: .leading, spacing: 6) {
                Text(context.attributes.groupName)
                    .font(.headline)
                Text("Следующая пара:")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                Text(context.state.lessonTitle)
                    .font(.title3)
                    .fontWeight(.medium)
                HStack {
                    Text("Ауд. \(context.state.room)")
                    Spacer()
                    Text("\(context.state.startTime, style: .time) — \(context.state.endTime, style: .time)")
                }
                .font(.footnote)
                .foregroundColor(.secondary)
                Text("До конца: \(context.state.endTime, style: .timer)")
                    .font(.caption)
                    .foregroundColor(.gray)
            }
            .padding()
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.center) {
                    VStack(spacing: 4) {
                        Text(context.state.lessonTitle)
                            .font(.headline)
                        Text("Ауд. \(context.state.room)")
                            .font(.subheadline)
                        Text("\(context.state.startTime, style: .time) — \(context.state.endTime, style: .time)")
                            .font(.footnote)
                            .foregroundColor(.secondary)
                        Text("До конца: \(context.state.endTime, style: .timer)")
                            .font(.caption2)
                            .foregroundColor(.gray)
                    }
                    .frame(maxWidth: .infinity)
                }
            } compactLeading: {
                Image(systemName: "book.fill")
            } compactTrailing: {
                Text("\(context.state.endTime, style: .timer)")
                    .font(.caption2)
            } minimal: {
                Image(systemName: "clock.fill")
            }
        }
    }
}
