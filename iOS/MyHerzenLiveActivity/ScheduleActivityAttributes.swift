//
//  ScheduleActivityAttributes.swift
//  MyHerzen
//
//  Created by Nicolas Forest on 11/4/25.
//

import ActivityKit
import Foundation

struct ScheduleActivityAttributes: ActivityAttributes {
    var groupName: String

    public struct ContentState: Codable, Hashable {
        var lessonTitle: String
        var room: String
        var startTime: Date
        var endTime: Date
    }
}
