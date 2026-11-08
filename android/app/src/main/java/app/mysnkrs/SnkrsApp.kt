package app.mysnkrs

import android.app.Application
import app.mysnkrs.data.Api
import app.mysnkrs.data.Prefs

class SnkrsApp : Application() {
    lateinit var prefs: Prefs
        private set
    lateinit var api: Api
        private set

    override fun onCreate() {
        super.onCreate()
        instance = this
        prefs = Prefs(this)
        api = Api { prefs.serverUrl }
    }

    companion object {
        lateinit var instance: SnkrsApp
            private set
    }
}
