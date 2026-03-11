import { Component, signal, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  protected readonly title = signal('frontend');
  private translate = inject(TranslateService);

  constructor() {
    this.translate.addLangs(['en', 'hi']);
    this.translate.setDefaultLang('en');
    this.translate.use('en');
  }
}
