package ru.moonbaystudio.myherzen.data.local.entity

import androidx.room.Entity

@Entity(
    tableName = "schedule_cache_days",
    primaryKeys = ["groupId", "date", "examOnly"]
)
data class LocalScheduleCacheDay(
    val groupId: Int,
    val date: String,
    val examOnly: Boolean
)
