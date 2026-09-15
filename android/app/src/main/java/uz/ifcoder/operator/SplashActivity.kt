package uz.ifcoder.operator

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import uz.ifcoder.operator.data.ApiClient
import uz.ifcoder.operator.ui.LoginActivity
import uz.ifcoder.operator.ui.TaskListActivity

class SplashActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val next = if (ApiClient.tokens().isLoggedIn()) {
            TaskListActivity::class.java
        } else {
            LoginActivity::class.java
        }
        startActivity(Intent(this, next))
        finish()
    }
}
