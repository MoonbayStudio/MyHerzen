import WidgetKit
import SwiftUI

@main
struct MyHerzenWidgetBundle: WidgetBundle {
    var body: some Widget {
        MyHerzenLiveActivity()

        if #available(iOSApplicationExtension 16.1, *) {
            ScheduleActivityLiveActivity()
        }
    }
}
